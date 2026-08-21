"""Lightweight semantic vector store and embedding similarity engine."""

import hashlib
import json
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from mitchell.memory.database import memory_db


def _generate_embedding(text: str, dim: int = 128) -> List[float]:
    """
    Generate a normalized semantic feature vector for text.
    Uses multi-hash n-gram frequency distribution with term weighting.
    """
    cleaned = text.lower().strip()
    words = cleaned.split()
    vector = [0.0] * dim

    if not words:
        return vector

    # Unigram and Bigram hashing
    tokens = list(words)
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")

    for token in tokens:
        # Hash token into multiple vector indices
        h1 = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % dim
        h2 = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % dim
        weight = 1.0 + math.log(len(token) + 1)

        vector[h1] += weight
        vector[h2] += weight * 0.5

    # L2 Normalize
    norm = math.sqrt(sum(v * v for v in vector))
    if norm > 0:
        vector = [v / norm for v in vector]

    return vector


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculate cosine similarity between two normalized vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    return sum(a * b for a, b in zip(vec_a, vec_b))


class VectorStore:
    """Local vector database for RAG retrieval over memory and skills."""

    def __init__(self) -> None:
        self.db = memory_db

    def index(self, entity_type: str, entity_id: str, text: str) -> str:
        """Store or update vector embedding for an entity."""
        emb = _generate_embedding(text)
        emb_json = json.dumps(emb)
        entry_id = f"{entity_type}:{entity_id}"

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO vector_store (id, entity_type, entity_id, text_content, embedding_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    text_content = excluded.text_content,
                    embedding_json = excluded.embedding_json,
                    created_at = CURRENT_TIMESTAMP
                """,
                (entry_id, entity_type, entity_id, text, emb_json),
            )
            conn.commit()

        return entry_id

    def search(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 5,
        threshold: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """Search vector database for closest semantic matches to query string."""
        query_vec = _generate_embedding(query)

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            if entity_type:
                cursor.execute(
                    "SELECT id, entity_type, entity_id, text_content, embedding_json FROM vector_store WHERE entity_type = ?",
                    (entity_type,),
                )
            else:
                cursor.execute("SELECT id, entity_type, entity_id, text_content, embedding_json FROM vector_store")

            rows = cursor.fetchall()

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for row in rows:
            try:
                emb = json.loads(row["embedding_json"])
                score = cosine_similarity(query_vec, emb)
                if score >= threshold:
                    scored.append((score, {
                        "id": row["id"],
                        "entity_type": row["entity_type"],
                        "entity_id": row["entity_id"],
                        "text": row["text_content"],
                        "similarity": round(score, 4),
                    }))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def delete(self, entity_type: str, entity_id: str) -> None:
        """Remove embedding from store."""
        entry_id = f"{entity_type}:{entity_id}"
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vector_store WHERE id = ?", (entry_id,))
            conn.commit()


vector_store = VectorStore()

__all__ = ["VectorStore", "vector_store", "cosine_similarity"]
