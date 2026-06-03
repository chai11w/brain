from __future__ import annotations

from pathlib import Path

from .config import BrainConfig, load_config
from .extractor import IngestResult, MemoryExtractor
from .llm import LLMClient
from .memory_view import MemoryDetail, MemorySummary, MemoryView
from .router import MemoryRouterBuilder, RouterBuildResult
from .schema import BrainSchema, SchemaInitResult
from .vault import SecureItemSecret, SecureItemSummary, SecureVault


class PersonalBrain:
    def __init__(self, config: BrainConfig | None = None):
        self.config = config or load_config()
        self.schema = BrainSchema(self.config.database_path)
        self.chat_model = LLMClient(self.config.chat_model)
        self.vault = SecureVault(self.schema)
        self.memory_view = MemoryView(self.schema)

    @classmethod
    def from_config_file(cls, path: str | Path = "config.json") -> "PersonalBrain":
        return cls(load_config(path))

    def handle_message(self, text: str, sender: str = "me", source: str = "wechat") -> str:
        return "Memory ingestion is not implemented yet. Run init-db to prepare the foundation."

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
                warning=result.warning,
            )
        return result

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
