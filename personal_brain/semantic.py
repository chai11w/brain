from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass

from .config import EmbeddingModelConfig
from .llm import EmbeddingClient
from .schema import BrainSchema


@dataclass(frozen=True)
class EmbedMemoriesResult:
    embedded_count: int
    skipped_count: int
    warning: str | None = None


@dataclass(frozen=True)
class RecallResult:
    memory_id: int
    score: float
    title: str | None
    content: str
    memory_type: str
    importance: float
    confidence: float
    created_at: str
    raw_message_id: int
    raw_content: str
    topics: list[str]


class SemanticMemory:
    """SQLite-backed embedding and recall layer for V0.1."""

    def __init__(
        self,
        schema: BrainSchema,
        embedding_client: EmbeddingClient,
        embedding_config: EmbeddingModelConfig,
    ):
        self.schema = schema
        self.embedding_client = embedding_client
        self.embedding_config = embedding_config

    def embed_missing_memories(self, limit: int = 100) -> EmbedMemoriesResult:
        self.schema.initialize()
        if not self.embedding_client.available:
            return EmbedMemoriesResult(
                embedded_count=0,
                skipped_count=0,
                warning=f"embedding model unavailable; set {self.embedding_config.api_key_env}",
            )

        with self.schema.connect() as conn:
            rows = conn.execute(
                """
                SELECT m.id, m.title, m.content, m.memory_type
                FROM memories m
                LEFT JOIN memory_embeddings e
                  ON e.memory_id = m.id
                 AND e.provider = ?
                 AND e.model = ?
                WHERE m.status = 'active'
                  AND e.memory_id IS NULL
                ORDER BY m.created_at ASC, m.id ASC
                LIMIT ?
                """,
                (self.embedding_config.provider, self.embedding_config.model, limit),
            ).fetchall()
            if not rows:
                return EmbedMemoriesResult(embedded_count=0, skipped_count=0)

            embedded = self._embed_rows(conn, rows)

        return EmbedMemoriesResult(
            embedded_count=embedded,
            skipped_count=max(0, len(rows) - embedded),
        )

    def embed_memories(self, memory_ids: list[int]) -> EmbedMemoriesResult:
        ids = sorted({int(memory_id) for memory_id in memory_ids if int(memory_id) > 0})
        if not ids:
            return EmbedMemoriesResult(embedded_count=0, skipped_count=0)

        self.schema.initialize()
        if not self.embedding_client.available:
            return EmbedMemoriesResult(
                embedded_count=0,
                skipped_count=0,
                warning=f"embedding model unavailable; set {self.embedding_config.api_key_env}",
            )

        placeholders = ",".join("?" for _ in ids)
        with self.schema.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT m.id, m.title, m.content, m.memory_type
                FROM memories m
                LEFT JOIN memory_embeddings e
                  ON e.memory_id = m.id
                 AND e.provider = ?
                 AND e.model = ?
                WHERE m.status = 'active'
                  AND e.memory_id IS NULL
                  AND m.id IN ({placeholders})
                ORDER BY m.created_at ASC, m.id ASC
                """,
                (self.embedding_config.provider, self.embedding_config.model, *ids),
            ).fetchall()
            if not rows:
                return EmbedMemoriesResult(embedded_count=0, skipped_count=0)

            embedded = self._embed_rows(conn, rows)

        return EmbedMemoriesResult(
            embedded_count=embedded,
            skipped_count=max(0, len(rows) - embedded),
        )

    def recall(self, query: str, limit: int = 8) -> list[RecallResult]:
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("recall query cannot be empty")
        self.schema.initialize()
        if not self.embedding_client.available:
            raise RuntimeError(f"embedding model unavailable; set {self.embedding_config.api_key_env}")

        query_vector = self.embedding_client.embed(clean_query)
        if not query_vector:
            raise RuntimeError("embedding model returned empty query vector")

        with self.schema.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    m.id, m.title, m.content, m.memory_type, m.importance, m.confidence,
                    m.created_at, m.raw_message_id, r.content AS raw_content,
                    e.vector_json
                FROM memory_embeddings e
                JOIN memories m ON m.id = e.memory_id
                JOIN raw_messages r ON r.id = m.raw_message_id
                WHERE e.provider = ?
                  AND e.model = ?
                  AND m.status = 'active'
                """,
                (self.embedding_config.provider, self.embedding_config.model),
            ).fetchall()
            scored: list[tuple[float, sqlite3.Row]] = []
            for row in rows:
                vector = json.loads(row["vector_json"])
                if isinstance(vector, list):
                    score = cosine_similarity(query_vector, [float(value) for value in vector])
                    scored.append((score, row))
            scored.sort(key=lambda item: item[0], reverse=True)
            results = [
                RecallResult(
                    memory_id=int(row["id"]),
                    score=score,
                    title=row["title"],
                    content=row["content"],
                    memory_type=row["memory_type"],
                    importance=float(row["importance"]),
                    confidence=float(row["confidence"]),
                    created_at=row["created_at"],
                    raw_message_id=int(row["raw_message_id"]),
                    raw_content=row["raw_content"],
                    topics=self._topics_for_memory(conn, int(row["id"])),
                )
                for score, row in scored[:limit]
            ]
        return results

    def _embedding_text(self, conn: sqlite3.Connection, memory_id: int, row: sqlite3.Row) -> str:
        topics = ", ".join(self._topics_for_memory(conn, memory_id))
        entities = ", ".join(self._entities_for_memory(conn, memory_id))
        parts = [
            f"title: {row['title'] or ''}",
            f"content: {row['content']}",
            f"type: {row['memory_type']}",
            f"topics: {topics}",
            f"entities: {entities}",
        ]
        return "\n".join(parts)

    def _embed_rows(self, conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> int:
        texts = [self._embedding_text(conn, int(row["id"]), row) for row in rows]
        vectors = self.embedding_client.embed_many(texts)
        embedded = 0
        for row, vector in zip(rows, vectors):
            memory_id = int(row["id"])
            dimension = len(vector)
            if self.embedding_config.dimension is not None and dimension != self.embedding_config.dimension:
                raise ValueError(
                    f"embedding dimension mismatch for memory {memory_id}: "
                    f"expected {self.embedding_config.dimension}, got {dimension}"
                )
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_embeddings (
                    memory_id, provider, model, vector_json, dimension
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    self.embedding_config.provider,
                    self.embedding_config.model,
                    json.dumps(vector, separators=(",", ":")),
                    dimension,
                ),
            )
            embedded += 1
        return embedded

    @staticmethod
    def _topics_for_memory(conn: sqlite3.Connection, memory_id: int) -> list[str]:
        rows = conn.execute(
            """
            SELECT t.name
            FROM memory_topics mt
            JOIN topics t ON t.id = mt.topic_id
            WHERE mt.memory_id = ?
            ORDER BY mt.confidence DESC, t.name ASC
            """,
            (memory_id,),
        ).fetchall()
        return [row["name"] for row in rows]

    @staticmethod
    def _entities_for_memory(conn: sqlite3.Connection, memory_id: int) -> list[str]:
        rows = conn.execute(
            """
            SELECT e.name, e.entity_type
            FROM memory_entities me
            JOIN entities e ON e.id = me.entity_id
            WHERE me.memory_id = ?
            ORDER BY me.confidence DESC, e.name ASC
            """,
            (memory_id,),
        ).fetchall()
        return [f"{row['name']}:{row['entity_type']}" for row in rows]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def format_recall_result(result: RecallResult) -> str:
    title = result.title or short_text(result.content, 60)
    topics = ", ".join(result.topics) if result.topics else "no topics"
    return (
        f"#{result.memory_id} score={result.score:.4f} {title}\n"
        f"  type={result.memory_type} importance={result.importance:.2f} "
        f"confidence={result.confidence:.2f} created={result.created_at}\n"
        f"  topics={topics}\n"
        f"  memory={short_text(result.content, 180)}\n"
        f"  evidence raw_message_id={result.raw_message_id}: {short_text(result.raw_content, 180)}"
    )


def short_text(text: str, limit: int) -> str:
    clean = " ".join(str(text).split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1] + "..."
