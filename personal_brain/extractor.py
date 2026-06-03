from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

from .config import ChatModelConfig
from .llm import LLMClient
from .schema import BrainSchema


PROMPT_VERSION = "memory-extraction-v1"


@dataclass(frozen=True)
class IngestResult:
    raw_message_id: int
    extraction_run_id: int | None
    memory_ids: list[int]
    topic_ids: list[int]
    entity_ids: list[int]
    should_remember: bool
    router_rebuilt: bool
    warning: str | None = None


class MemoryExtractor:
    """Turn casual user input into AI-generated atomic memories."""

    def __init__(
        self,
        schema: BrainSchema,
        chat_model: LLMClient,
        chat_config: ChatModelConfig,
    ):
        self.schema = schema
        self.chat_model = chat_model
        self.chat_config = chat_config

    def ingest(
        self,
        text: str,
        source: str = "cli",
        sender: str = "me",
        metadata: dict[str, Any] | None = None,
    ) -> IngestResult:
        content = text.strip()
        if not content:
            raise ValueError("ingest text cannot be empty")

        self.schema.initialize()
        raw_message_id = self._insert_raw_message(content, source, sender, metadata)

        if not self.chat_model.available:
            extraction_run_id = self._record_failed_run(
                raw_message_id,
                content,
                "chat model is not available",
            )
            self._mark_raw_status(raw_message_id, "failed")
            return IngestResult(
                raw_message_id=raw_message_id,
                extraction_run_id=extraction_run_id,
                memory_ids=[],
                topic_ids=[],
                entity_ids=[],
                should_remember=False,
                router_rebuilt=False,
                warning=f"chat model unavailable; set {self.chat_config.api_key_env}",
            )

        try:
            output_text = self._call_model(content)
            payload = parse_json_object(output_text)
        except Exception as exc:
            extraction_run_id = self._record_failed_run(raw_message_id, content, str(exc))
            self._mark_raw_status(raw_message_id, "failed")
            raise RuntimeError(f"memory extraction failed: {exc}") from exc

        return self._persist_extraction(raw_message_id, content, payload)

    def _call_model(self, content: str) -> str:
        system_prompt = (
            "你是 AI-native Personal Brain 的记忆提取器。"
            "你的任务不是聊天，而是把用户的随意输入整理成长期记忆。"
            "你可以去掉口语、重复和噪音，但不能改变用户原意。"
            "如果一句话包含多个独立想法，请拆成多条 atomic memories。"
            "只输出 JSON，不要输出 Markdown，不要解释。"
        )
        user_prompt = {
            "task": "extract_personal_memory",
            "rules": [
                "Preserve the user's meaning.",
                "Rewrite into concise third-person memory statements.",
                "Use dynamic topics; do not force fixed categories.",
                "Only remember durable preferences, decisions, ideas, principles, plans, or self-knowledge.",
                "If the input is too trivial to remember, set should_remember=false.",
            ],
            "output_schema": {
                "should_remember": True,
                "reason": "why this should or should not be remembered",
                "atomic_memories": [
                    {
                        "title": "short title",
                        "content": "AI-rewritten atomic memory",
                        "memory_type": "preference|principle|decision|idea|plan|reflection|fact|other",
                        "importance": 0.0,
                        "confidence": 0.0,
                        "topics": [
                            {
                                "name": "dynamic topic name",
                                "description": "what this topic means",
                                "confidence": 0.0,
                                "reason": "why linked",
                            }
                        ],
                        "entities": [
                            {
                                "name": "entity name",
                                "type": "person|product|tool|project|concept|other",
                                "description": "optional short description",
                                "confidence": 0.0,
                            }
                        ],
                    }
                ],
            },
            "user_input": content,
        }
        answer = self.chat_model.chat(
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_prompt, ensure_ascii=False),
                },
            ],
            temperature=0.1,
        )
        if not answer:
            raise RuntimeError("model returned empty response")
        return answer

    def _insert_raw_message(
        self,
        content: str,
        source: str,
        sender: str,
        metadata: dict[str, Any] | None,
    ) -> int:
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        with self.schema.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO raw_messages (content, source, sender, metadata_json, processed_status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (content, source, sender, metadata_json),
            )
            return int(cursor.lastrowid)

    def _record_failed_run(self, raw_message_id: int, content: str, error: str) -> int:
        with self.schema.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO memory_extraction_runs (
                    raw_message_id, model_provider, model_name, prompt_version,
                    input_hash, output_json, status, error
                )
                VALUES (?, ?, ?, ?, ?, ?, 'failed', ?)
                """,
                (
                    raw_message_id,
                    self.chat_config.provider,
                    self.chat_config.model,
                    PROMPT_VERSION,
                    input_hash(content),
                    "{}",
                    error,
                ),
            )
            return int(cursor.lastrowid)

    def _persist_extraction(
        self,
        raw_message_id: int,
        raw_content: str,
        payload: dict[str, Any],
    ) -> IngestResult:
        should_remember = bool(payload.get("should_remember", False))
        memories = payload.get("atomic_memories") or []
        if not isinstance(memories, list):
            raise ValueError("atomic_memories must be a list")

        output_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        memory_ids: list[int] = []
        topic_ids: list[int] = []
        entity_ids: list[int] = []

        with self.schema.connect() as conn:
            run_cursor = conn.execute(
                """
                INSERT INTO memory_extraction_runs (
                    raw_message_id, model_provider, model_name, prompt_version,
                    input_hash, output_json, status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'succeeded')
                """,
                (
                    raw_message_id,
                    self.chat_config.provider,
                    self.chat_config.model,
                    PROMPT_VERSION,
                    input_hash(raw_content),
                    output_json,
                ),
            )
            extraction_run_id = int(run_cursor.lastrowid)

            if should_remember:
                for item in memories:
                    memory_id = self._insert_memory(conn, raw_message_id, extraction_run_id, item)
                    memory_ids.append(memory_id)
                    topic_ids.extend(self._link_topics(conn, memory_id, item.get("topics") or []))
                    entity_ids.extend(self._link_entities(conn, memory_id, item.get("entities") or []))

            status = "processed" if should_remember else "ignored"
            conn.execute(
                """
                UPDATE raw_messages
                SET processed_status = ?, processed_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (status, raw_message_id),
            )

        return IngestResult(
            raw_message_id=raw_message_id,
            extraction_run_id=extraction_run_id,
            memory_ids=memory_ids,
            topic_ids=sorted(set(topic_ids)),
            entity_ids=sorted(set(entity_ids)),
            should_remember=should_remember,
            router_rebuilt=False,
            warning=None if should_remember else "model decided not to remember this input",
        )

    def _insert_memory(
        self,
        conn: sqlite3.Connection,
        raw_message_id: int,
        extraction_run_id: int,
        item: dict[str, Any],
    ) -> int:
        content = clean_required_text(item.get("content"), "memory content")
        title = clean_optional_text(item.get("title"))
        memory_type = clean_optional_text(item.get("memory_type")) or "other"
        importance = clamp_score(item.get("importance"), default=0.5)
        confidence = clamp_score(item.get("confidence"), default=0.7)
        cursor = conn.execute(
            """
            INSERT INTO memories (
                raw_message_id, extraction_run_id, content, title,
                memory_type, importance, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raw_message_id,
                extraction_run_id,
                content,
                title,
                memory_type,
                importance,
                confidence,
            ),
        )
        return int(cursor.lastrowid)

    def _link_topics(
        self,
        conn: sqlite3.Connection,
        memory_id: int,
        topics: list[Any],
    ) -> list[int]:
        topic_ids: list[int] = []
        for topic in topics:
            if isinstance(topic, str):
                topic_data = {"name": topic}
            elif isinstance(topic, dict):
                topic_data = topic
            else:
                continue
            name = clean_optional_text(topic_data.get("name"))
            if not name:
                continue
            description = clean_optional_text(topic_data.get("description"))
            confidence = clamp_score(topic_data.get("confidence"), default=0.7)
            reason = clean_optional_text(topic_data.get("reason"))
            topic_id = upsert_topic(conn, name, description)
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_topics (memory_id, topic_id, confidence, reason)
                VALUES (?, ?, ?, ?)
                """,
                (memory_id, topic_id, confidence, reason),
            )
            topic_ids.append(topic_id)
        return topic_ids

    def _link_entities(
        self,
        conn: sqlite3.Connection,
        memory_id: int,
        entities: list[Any],
    ) -> list[int]:
        entity_ids: list[int] = []
        for entity in entities:
            if isinstance(entity, str):
                entity_data = {"name": entity, "type": "other"}
            elif isinstance(entity, dict):
                entity_data = entity
            else:
                continue
            name = clean_optional_text(entity_data.get("name"))
            if not name:
                continue
            entity_type = clean_optional_text(entity_data.get("type")) or clean_optional_text(entity_data.get("entity_type")) or "other"
            description = clean_optional_text(entity_data.get("description"))
            confidence = clamp_score(entity_data.get("confidence"), default=0.7)
            entity_id = upsert_entity(conn, name, entity_type, description)
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_entities (memory_id, entity_id, confidence)
                VALUES (?, ?, ?)
                """,
                (memory_id, entity_id, confidence),
            )
            entity_ids.append(entity_id)
        return entity_ids

    def _mark_raw_status(self, raw_message_id: int, status: str) -> None:
        with self.schema.connect() as conn:
            conn.execute(
                """
                UPDATE raw_messages
                SET processed_status = ?, processed_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (status, raw_message_id),
            )


def input_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end < start:
            raise
        payload = json.loads(cleaned[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("model output must be a JSON object")
    return payload


def clean_required_text(value: Any, label: str) -> str:
    text = clean_optional_text(value)
    if not text:
        raise ValueError(f"{label} is required")
    return text


def clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clamp_score(value: Any, default: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    return max(0.0, min(1.0, score))


def upsert_topic(conn: sqlite3.Connection, name: str, description: str | None) -> int:
    conn.execute(
        """
        INSERT INTO topics (name, description)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET
            description = COALESCE(excluded.description, topics.description),
            updated_at = datetime('now', 'localtime')
        """,
        (name, description),
    )
    row = conn.execute("SELECT id FROM topics WHERE name = ?", (name,)).fetchone()
    return int(row["id"])


def upsert_entity(
    conn: sqlite3.Connection,
    name: str,
    entity_type: str,
    description: str | None,
) -> int:
    conn.execute(
        """
        INSERT INTO entities (name, entity_type, description)
        VALUES (?, ?, ?)
        ON CONFLICT(name, entity_type) DO UPDATE SET
            description = COALESCE(excluded.description, entities.description)
        """,
        (name, entity_type, description),
    )
    row = conn.execute(
        "SELECT id FROM entities WHERE name = ? AND entity_type = ?",
        (name, entity_type),
    ).fetchone()
    return int(row["id"])

