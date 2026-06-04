from __future__ import annotations

from pathlib import Path

from .answer import AnswerEngine, AnswerResult
from .config import BrainConfig, load_config
from .extractor import IngestResult, MemoryExtractor
from .llm import EmbeddingClient, LLMClient
from .memory_view import MemoryDetail, MemorySummary, MemoryView
from .router import MemoryRouterBuilder, RouterBuildResult
from .schema import BrainSchema, SchemaInitResult
from .semantic import EmbedMemoriesResult, RecallResult, SemanticMemory
from .vault import SecureItemSecret, SecureItemSummary, SecureVault


class PersonalBrain:
    def __init__(self, config: BrainConfig | None = None):
        self.config = config or load_config()
        self.schema = BrainSchema(self.config.database_path)
        self.chat_model = LLMClient(self.config.chat_model)
        self.embedding_model = EmbeddingClient(self.config.embedding_model)
        self.vault = SecureVault(self.schema)
        self.memory_view = MemoryView(self.schema)
        self.semantic_memory = SemanticMemory(
            schema=self.schema,
            embedding_client=self.embedding_model,
            embedding_config=self.config.embedding_model,
        )
        self.answer_engine = AnswerEngine(
            semantic_memory=self.semantic_memory,
            chat_model=self.chat_model,
        )

    @classmethod
    def from_config_file(cls, path: str | Path = "config.json") -> "PersonalBrain":
        return cls(load_config(path))

    def handle_message(self, text: str, sender: str = "me", source: str = "wechat") -> str:
        message = text.strip()
        if not message:
            return "我在。"
        try:
            result = self.ingest(message, source=source, sender=sender)
        except Exception as exc:
            return f"暂时没记住：{exc}"
        if result.memory_ids:
            if result.warning:
                return f"已记住，但后续处理有提醒：{result.warning}"
            return "已记住。"
        if result.warning:
            return f"已收到，但没有写入长期记忆：{result.warning}"
        return "已收到。"

    def init_db(self) -> SchemaInitResult:
        return self.schema.initialize()

    def ingest(
        self,
        text: str,
        source: str = "cli",
        sender: str = "me",
        rebuild_router: bool = True,
    ) -> IngestResult:
        extractor = MemoryExtractor(
            schema=self.schema,
            chat_model=self.chat_model,
            chat_config=self.config.chat_model,
        )
        result = extractor.ingest(text=text, source=source, sender=sender)
        warning = result.warning
        if result.memory_ids:
            warning = self._embed_ingested_memories(result.memory_ids, warning)
        if rebuild_router:
            self.build_router()
            return IngestResult(
                raw_message_id=result.raw_message_id,
                extraction_run_id=result.extraction_run_id,
                memory_ids=result.memory_ids,
                topic_ids=result.topic_ids,
                entity_ids=result.entity_ids,
                should_remember=result.should_remember,
                router_rebuilt=True,
                warning=warning,
            )
        if warning != result.warning:
            return IngestResult(
                raw_message_id=result.raw_message_id,
                extraction_run_id=result.extraction_run_id,
                memory_ids=result.memory_ids,
                topic_ids=result.topic_ids,
                entity_ids=result.entity_ids,
                should_remember=result.should_remember,
                router_rebuilt=result.router_rebuilt,
                warning=warning,
            )
        return result

    def _embed_ingested_memories(self, memory_ids: list[int], warning: str | None) -> str | None:
        if not self.config.embedding_model.enabled:
            return warning
        try:
            result = self.semantic_memory.embed_memories(memory_ids)
        except Exception as exc:
            return combine_warning(warning, f"embedding failed: {exc}")
        if result.warning:
            return combine_warning(warning, result.warning)
        return warning

    def build_router(self) -> RouterBuildResult:
        builder = MemoryRouterBuilder(
            database_path=self.config.database_path,
            memory_dir=self.config.memory_dir,
            brain_index_path=self.config.brain_index_path,
        )
        return builder.build()

    def test_chat(self, prompt: str) -> str:
        if not self.chat_model.available:
            return (
                f"chat model is not available. Enable chat_model and set "
                f"{self.config.chat_model.api_key_env}."
            )
        answer = self.chat_model.chat(
            [
                {
                    "role": "system",
                    "content": "你是 Personal Brain 的模型连通性测试助手。请简洁回答。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return answer or "empty response"

    def stats(self) -> str:
        counts = self.schema.stats()
        if not counts:
            return "database has no Personal Brain tables yet"
        return "\n".join(f"{table}: {count}" for table, count in counts.items())

    def secure_add(
        self,
        label: str,
        secret_type: str,
        secret: str,
        master_password: str,
        username: str | None = None,
        note: str | None = None,
    ) -> int:
        return self.vault.add_item(
            label=label,
            secret_type=secret_type,
            secret=secret,
            master_password=master_password,
            username=username,
            note=note,
        )

    def secure_list(self) -> list[SecureItemSummary]:
        return self.vault.list_items()

    def secure_get(self, label: str, master_password: str) -> SecureItemSecret:
        return self.vault.get_item(label, master_password)

    def memory_list(self, limit: int = 20) -> list[MemorySummary]:
        return self.memory_view.list_memories(limit=limit)

    def memory_show(self, memory_id: int) -> MemoryDetail:
        return self.memory_view.show_memory(memory_id)

    def embed_missing_memories(self, limit: int = 100) -> EmbedMemoriesResult:
        return self.semantic_memory.embed_missing_memories(limit=limit)

    def recall(self, query: str, limit: int = 8) -> list[RecallResult]:
        return self.semantic_memory.recall(query=query, limit=limit)

    def ask(self, question: str, recall_limit: int = 8, evidence_limit: int = 5) -> AnswerResult:
        return self.answer_engine.ask(
            question=question,
            recall_limit=recall_limit,
            evidence_limit=evidence_limit,
        )


def combine_warning(first: str | None, second: str | None) -> str | None:
    if first and second:
        return f"{first}; {second}"
    return first or second
