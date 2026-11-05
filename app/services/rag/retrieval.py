from dataclasses import dataclass

import numpy as np
from sqlalchemy import select

from ...extensions import db
from ...models.document import Chunk
from .embeddings import get_embeddings


@dataclass
class Passage:
    index: int  # 1-based, matches the [n] citations in the answer
    page: int
    text: str
    score: float  # cosine similarity, higher is closer


def search(user_id: int, document_id: int, query: str, k: int) -> list[Passage]:
    """Top-k chunks of ONE document owned by ONE user. Both filters are always applied."""
    query_vec = get_embeddings().embed_query(query)
    scope = (Chunk.user_id == user_id, Chunk.document_id == document_id)

    if db.session.get_bind().dialect.name == "postgresql":
        distance = Chunk.embedding.cosine_distance(query_vec).label("distance")
        rows = db.session.execute(select(Chunk, distance).where(*scope).order_by(distance).limit(k)).all()
        scored = [(chunk, 1.0 - float(dist)) for chunk, dist in rows]
    else:  # SQLite (tests): brute force in numpy
        chunks = db.session.scalars(select(Chunk).where(*scope)).all()
        q = np.asarray(query_vec, dtype=float)
        scored = []
        for chunk in chunks:
            v = np.asarray(chunk.embedding, dtype=float)
            denom = (np.linalg.norm(q) * np.linalg.norm(v)) or 1.0
            scored.append((chunk, float(q @ v / denom)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        scored = scored[:k]

    return [Passage(i, c.page, c.content, round(score, 4)) for i, (c, score) in enumerate(scored, start=1)]
