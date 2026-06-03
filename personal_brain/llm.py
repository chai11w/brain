from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .config import ChatModelConfig


class LLMClient:
    def __init__(self, config: ChatModelConfig):
        self.config = config

    @property
    def available(self) -> bool:
        return self.config.enabled and bool(os.environ.get(self.config.api_key_env))

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        response_format: dict | None = None,
    ) -> str | None:
        if not self.available:
            return None
        if self.config.provider != "openai_compatible":
            raise ValueError(f"unsupported llm provider: {self.config.provider}")

        api_key = os.environ[self.config.api_key_env]
        endpoint = self.config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"model HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"model call failed: {exc}") from exc

        message = data["choices"][0]["message"]
        content = message.get("content")
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif isinstance(item, str):
                    parts.append(item)
            return "\n".join(part for part in parts if part).strip()
        return str(content or "").strip()
