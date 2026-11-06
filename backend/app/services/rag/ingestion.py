"""PDF -> pages -> chunks -> embeddings -> rows. Runs off the request thread."""
import io
from time import perf_counter

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy import insert

from ...extensions import db
from ...models.document import STATUS_FAILED, STATUS_READY, Chunk, Document
from .embeddings import get_embeddings

EMBED_BATCH = 256
REMOTE_EMBED_BATCH = 64


class IngestionError(Exception):
    """A problem with the user's file. The message is safe to show in the UI."""


def extract_pages(pdf_bytes: bytes, max_pages: int) -> list[tuple[int, str]]:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if reader.is_encrypted and not reader.decrypt(""):
            raise IngestionError("Password-protected PDFs aren't supported.")
        total = len(reader.pages)
    except IngestionError:
        raise
    except Exception as exc:  # pypdf raises many types on malformed input
        raise IngestionError("This PDF couldn't be read. The file may be corrupted.") from exc

    if total > max_pages:
        raise IngestionError(f"This PDF has {total} pages. The limit is {max_pages}.")

    pages = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append((number, text.replace("\x00", "")))  # Postgres rejects NUL characters
    return pages


def ingest_document(app, document_id: int, pdf_bytes: bytes) -> None:
    with app.app_context():
        try:
            _ingest(app, document_id, pdf_bytes)
        except IngestionError as exc:
            _mark_failed(document_id, str(exc))
        except Exception:
            app.logger.exception("Ingestion crashed for document %s", document_id)
            _mark_failed(document_id, "Something went wrong while processing this PDF. Please try again.")


def _ingest(app, document_id: int, pdf_bytes: bytes) -> None:
    started = perf_counter()
    cfg = app.config
    doc = db.session.get(Document, document_id)
    if doc is None:  # deleted while queued
        return

    stage_started = perf_counter()
    pages = extract_pages(pdf_bytes, cfg["MAX_PDF_PAGES"])
    extract_seconds = perf_counter() - stage_started
    lc_docs = [LCDocument(page_content=t, metadata={"page": n}) for n, t in pages if t.strip()]
    if not lc_docs:
        raise IngestionError("No text found. Scanned PDFs need OCR, which isn't supported yet.")

    stage_started = perf_counter()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg["CHUNK_SIZE"], chunk_overlap=cfg["CHUNK_OVERLAP"]
    )
    chunks = [c for c in splitter.split_documents(lc_docs) if c.page_content.strip()]
    chunk_seconds = perf_counter() - stage_started

    stage_started = perf_counter()
    embeddings = get_embeddings()
    model_seconds = perf_counter() - stage_started
    texts = [c.page_content for c in chunks]
    vectors: list[list[float]] = []
    stage_started = perf_counter()
    batch_size = (
        REMOTE_EMBED_BATCH
        if cfg["EMBEDDINGS_PROVIDER"] in {"voyage", "openai"}
        else EMBED_BATCH
    )
    for i in range(0, len(texts), batch_size):
        vectors.extend(embeddings.embed_documents(texts[i : i + batch_size]))
    embed_seconds = perf_counter() - stage_started

    if len(vectors) != len(chunks):
        raise IngestionError(
            f"The embedding service returned {len(vectors)} vectors for {len(chunks)} passages."
        )
    if any(len(vector) != cfg["EMBEDDING_DIM"] for vector in vectors):
        raise IngestionError(
            f"Embedding size mismatch: expected {cfg['EMBEDDING_DIM']} dimensions for every passage."
        )

    stage_started = perf_counter()
    db.session.execute(
        insert(Chunk),
        [
            {
                "document_id": doc.id,
                "user_id": doc.user_id,
                "page": chunk.metadata["page"],
                "position": position,
                "content": chunk.page_content,
                "embedding": vector,
            }
            for position, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
        ],
    )
    doc.page_count = len(pages)
    doc.chunk_count = len(chunks)
    doc.status = STATUS_READY
    doc.error = None
    db.session.commit()
    save_seconds = perf_counter() - stage_started
    app.logger.info(
        "Ingested document %s: %d pages, %d chunks; extract=%.2fs chunk=%.2fs "
        "model=%.2fs "
        "embed=%.2fs save=%.2fs total=%.2fs",
        document_id,
        len(pages),
        len(chunks),
        extract_seconds,
        chunk_seconds,
        model_seconds,
        embed_seconds,
        save_seconds,
        perf_counter() - started,
    )


def _mark_failed(document_id: int, message: str) -> None:
    db.session.rollback()
    doc = db.session.get(Document, document_id)
    if doc is None:
        return
    doc.status = STATUS_FAILED
    doc.error = message[:500]
    db.session.commit()
