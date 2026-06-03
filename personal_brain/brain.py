from __future__ import annotations

from pathlib import Path

from .config import BrainConfig, load_config
from .llm import LLMClient
from .router import MemoryRouterBuilder, RouterBuildResult
from .schema import BrainSchema, SchemaInitResult


class PersonalBrain:
    def __init__(self, config: BrainConfig | None = None):
        self.config = config or load_config()
        self.schema = BrainSchema(self.config.database_path)
        self.chat_model = LLMClient(self.config.chat_model)

    @classmethod
    def from_config_file(cls, path: str | Path = "config.json") -> "PersonalBrain":
        return cls(load_config(path))

    def handle_message(self, text: str, sender: str = "me", source: str = "wechat") -> str:
        return "Memory ingestion is not implemented yet. Run init-db to prepare the foundation."

    def init_db(self) -> SchemaInitResult:
        return self.schema.initialize()

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
