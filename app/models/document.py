from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..config import EMBEDDING_DIM
from ..extensions import db
from .base import TimestampMixin

STATUS_PROCESSING = "processing"
STATUS_READY = "ready"
STATUS_FAILED = "failed"


class Document(TimestampMixin, db.Model):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default=STATUS_PROCESSING)
    error: Mapped[str | None] = mapped_column(String(500), default=None)
    page_count: Mapped[int | None] = mapped_column(default=None)
    chunk_count: Mapped[int | None] = mapped_column(default=None)


class Chunk(db.Model):
    """A passage of a document plus its embedding.

    `user_id` is denormalised on purpose: every similarity query filters by it, so one user's
    question can never retrieve another user's text even if a document id were guessed.
    """

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    page: Mapped[int]
    position: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    # pgvector on Postgres; plain JSON on SQLite so the test-suite runs without a server.
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM).with_variant(JSON(), "sqlite"))
