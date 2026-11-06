import json

from flask import Response, current_app, g, jsonify, request, stream_with_context
from sqlalchemy import delete, func
from werkzeug.utils import secure_filename

from ..errors import BadGateway, BadRequest, Conflict, Forbidden, NotFound
from ..extensions import db
from ..models.document import STATUS_READY, Chunk, Document
from ..schemas import AskSchema, document_out, documents_out
from ..services.rag import jobs
from ..services.rag.chain import build_chain, chain_inputs, get_chat_model
from ..services.rag.ingestion import ingest_document
from ..services.rag.retrieval import search
from ..utils import get_json_body


def _owned_document(doc_id: int) -> Document:
    """404 (not 403) for other people's documents, so ids can't be probed."""
    doc = db.session.get(Document, doc_id)
    if doc is None or doc.user_id != g.current_user.id:
        raise NotFound("Document not found")
    return doc


def upload_document():
    cfg = current_app.config
    file = request.files.get("file")
    if file is None or not file.filename:
        raise BadRequest("Attach a PDF in the 'file' field.", code="file_required")

    data = file.read()
    if not data.startswith(b"%PDF-"):  # check content, not the filename or client MIME type
        raise BadRequest("That file isn't a PDF.", code="invalid_file")

    owned = db.session.scalar(
        db.select(func.count(Document.id)).where(Document.user_id == g.current_user.id)
    )
    if owned >= cfg["MAX_DOCS_PER_USER"]:
        raise Forbidden(
            f"You've reached the limit of {cfg['MAX_DOCS_PER_USER']} documents. Delete one to upload another.",
            code="quota_exceeded",
        )

    doc = Document(
        user_id=g.current_user.id,
        filename=(secure_filename(file.filename) or "document.pdf")[:255],
        size_bytes=len(data),
    )
    db.session.add(doc)
    db.session.commit()

    jobs.submit(ingest_document, current_app._get_current_object(), doc.id, data)
    db.session.refresh(doc)  # sync ingestion may already have changed it
    return jsonify({"data": document_out.dump(doc)}), 202


def list_documents():
    docs = db.session.scalars(
        db.select(Document).where(Document.user_id == g.current_user.id).order_by(Document.id.desc())
    ).all()
    return jsonify({"data": documents_out.dump(docs)}), 200


def get_document(doc_id: int):
    return jsonify({"data": document_out.dump(_owned_document(doc_id))}), 200


def delete_document(doc_id: int):
    doc = _owned_document(doc_id)
    db.session.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    db.session.delete(doc)
    db.session.commit()
    return "", 204


def _sse(event: str, payload) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def ask(doc_id: int):
    doc = _owned_document(doc_id)
    if doc.status != STATUS_READY:
        raise Conflict(f"This document is {doc.status}. Ask again once it's ready.", code="document_not_ready")

    data = AskSchema().load(get_json_body())
    llm = get_chat_model()  # fail fast (503) before any streaming starts

    passages = search(g.current_user.id, doc.id, data["question"], current_app.config["TOP_K"])
    sources = [{"index": p.index, "page": p.page, "text": p.text, "score": p.score} for p in passages]
    chain = build_chain(llm)
    inputs = chain_inputs(doc.filename, data["question"], passages, data["history"])

    if not data["stream"]:
        try:
            answer = chain.invoke(inputs)
        except Exception as exc:
            current_app.logger.exception("LLM call failed")
            raise BadGateway("The AI model request failed. Please try again.", code="llm_error") from exc
        return jsonify({"data": {"answer": answer, "sources": sources}}), 200

    def generate():
        yield _sse("sources", sources)
        try:
            for token in chain.stream(inputs):
                if token:
                    yield _sse("token", {"text": token})
        except Exception:
            current_app.logger.exception("LLM stream failed")
            yield _sse("error", {"code": "llm_error", "message": "The AI model request failed. Please try again."})
            return
        yield _sse("done", {})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # no proxy buffering
    )
