from __future__ import annotations

import argparse
import json
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from personal_brain import PersonalBrain  # noqa: E402
from personal_brain.answer import AnswerResult  # noqa: E402
from personal_brain.llm import get_secret_env  # noqa: E402
from personal_brain.memory_view import MemoryDetail  # noqa: E402


FEISHU_OPEN_API = "https://open.feishu.cn/open-apis"


@dataclass(frozen=True)
class FeishuOptions:
    mode: str
    ask_prefix: str
    ack_message: str
    working_reaction: str | None
    verification_token: str | None
    app_id: str
    app_secret: str
    dry_run: bool


@dataclass(frozen=True)
class BridgeReply:
    text: str
    action: str
    raw_message_id: int | None = None
    evidence: list[dict[str, Any]] | None = None


class FeishuClient:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token: str | None = None
        self._token_expires_at = 0.0
        self._lock = threading.Lock()

    def reply_text(self, message_id: str, text: str) -> None:
        token = self.tenant_access_token()
        body = {
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        request_json(
            f"{FEISHU_OPEN_API}/im/v1/messages/{message_id}/reply",
            method="POST",
            payload=body,
            headers={"Authorization": f"Bearer {token}"},
        )

    def add_reaction(self, message_id: str, emoji_type: str) -> None:
        token = self.tenant_access_token()
        body = {"reaction_type": {"emoji_type": emoji_type}}
        request_json(
            f"{FEISHU_OPEN_API}/im/v1/messages/{message_id}/reactions",
            method="POST",
            payload=body,
            headers={"Authorization": f"Bearer {token}"},
        )

    def tenant_access_token(self) -> str:
        now = time.time()
        with self._lock:
            if self._tenant_access_token and now < self._token_expires_at:
                return self._tenant_access_token
            data = request_json(
                f"{FEISHU_OPEN_API}/auth/v3/tenant_access_token/internal",
                method="POST",
                payload={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            token = str(data.get("tenant_access_token") or "")
            if not token:
                raise RuntimeError(f"failed to get tenant_access_token: {data}")
            expire = int(data.get("expire") or 7200)
            self._tenant_access_token = token
            self._token_expires_at = now + max(60, expire - 120)
            return token


class FeishuBrainBridge:
    def __init__(self, brain: PersonalBrain, client: FeishuClient, options: FeishuOptions):
        self.brain = brain
        self.client = client
        self.options = options
        self._seen_event_ids: set[str] = set()
        self._lock = threading.Lock()

    def handle_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "encrypt" in payload:
            return {"ok": False, "error": "encrypted events are not supported in MVP; leave Encrypt Key empty"}

        if is_url_verification(payload):
            if not self._valid_token(payload):
                return {"ok": False, "error": "invalid verification token"}
            return {"challenge": payload.get("challenge")}

        if not self._valid_token(payload):
            return {"ok": False, "error": "invalid verification token"}

        header = payload.get("header") or {}
        event_type = header.get("event_type") or payload.get("type")
        if event_type != "im.message.receive_v1":
            return {"ok": True, "ignored": event_type or "unknown"}

        event_id = str(header.get("event_id") or "")
        if event_id and event_id in self._seen_event_ids:
            return {"ok": True, "duplicate": event_id}
        if event_id:
            self._seen_event_ids.add(event_id)

        event = payload.get("event") or {}
        message = event.get("message") or {}
        message_id = str(message.get("message_id") or "")
        text = extract_text_message(message)
        sender = extract_sender(event)
        if not message_id or not text:
            return {"ok": True, "ignored": "non-text-or-missing-message"}

        self._mark_working_async(message_id)
        thread = threading.Thread(
            target=self._process_and_reply,
            args=(message_id, text, sender),
            daemon=True,
        )
        thread.start()
        return {"ok": True, "accepted": message_id}

    def _process_and_reply(self, message_id: str, text: str, sender: str) -> None:
        print(f"received from {sender}: {text}", flush=True)
        started_at = time.perf_counter()
        status = "succeeded"
        error = None
        bridge_reply: BridgeReply | None = None
        with self._lock:
            try:
                bridge_reply = self._reply_for_text(text, sender)
                reply = bridge_reply.text
            except Exception as exc:
                status = "failed"
                error = str(exc)
                reply = f"暂时处理失败：{exc}"
                bridge_reply = BridgeReply(text=reply, action="error")

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        self._record_interaction(
            message_id=message_id,
            text=text,
            sender=sender,
            reply=bridge_reply,
            status=status,
            error=error,
            latency_ms=latency_ms,
        )

        if self.options.dry_run:
            print(f"dry-run reply to {message_id}: {reply}", flush=True)
            return

        try:
            self.client.reply_text(message_id, reply)
            print(f"replied to {message_id}: {reply}", flush=True)
        except Exception as exc:
            print(f"failed to reply {message_id}: {exc}", file=sys.stderr, flush=True)

    def _reply_for_text(self, text: str, sender: str) -> BridgeReply:
        if self.options.mode == "remember":
            return self._remember_text(text, sender)
        if self.options.mode == "ask":
            result = self.brain.ask(text)
            return BridgeReply(text=result.answer, action="ask", evidence=answer_evidence_payload(result))
        if self.options.mode == "auto":
            question = extract_question(text, self.options.ask_prefix)
            if question:
                result = self.brain.ask(question)
                return BridgeReply(text=result.answer, action="ask", evidence=answer_evidence_payload(result))
            return self._remember_text(text, sender)
        raise ValueError(f"unsupported mode: {self.options.mode}")

    def _mark_working_async(self, message_id: str) -> None:
        if not self.options.working_reaction or self.options.dry_run:
            return
        thread = threading.Thread(
            target=self._mark_working,
            args=(message_id,),
            daemon=True,
        )
        thread.start()

    def _mark_working(self, message_id: str) -> None:
        emoji_type = self.options.working_reaction
        if not emoji_type or self.options.dry_run:
            return
        try:
            self.client.add_reaction(message_id, emoji_type)
            print(f"reacted to {message_id}: {emoji_type}", flush=True)
        except Exception as exc:
            print(f"failed to react {message_id}: {exc}", file=sys.stderr, flush=True)

    def _remember_text(self, text: str, sender: str) -> BridgeReply:
        result = self.brain.ingest(text, sender=sender, source="feishu")
        if result.memory_ids:
            details = [self.brain.memory_show(memory_id) for memory_id in result.memory_ids]
            reply = format_remembered_reply(self.options.ack_message, details)
            if result.warning:
                reply = f"{reply}\n\n提醒：{result.warning}"
            return BridgeReply(text=reply, action="remember", raw_message_id=result.raw_message_id)
        if result.warning:
            return BridgeReply(
                text="小柴收到了，不过这句不像长期记忆，我先不存。",
                action="ignored",
                raw_message_id=result.raw_message_id,
            )
        return BridgeReply(
            text=self.options.ack_message or "小柴记住了。",
            action="received",
            raw_message_id=result.raw_message_id,
        )

    def _record_interaction(
        self,
        *,
        message_id: str,
        text: str,
        sender: str,
        reply: BridgeReply,
        status: str,
        error: str | None,
        latency_ms: int,
    ) -> None:
        try:
            self.brain.record_interaction(
                message_id=message_id,
                source="feishu",
                sender=sender,
                user_text=text,
                mode=self.options.mode,
                action=reply.action,
                raw_message_id=reply.raw_message_id,
                reply_text=reply.text,
                evidence=reply.evidence,
                status=status,
                error=error,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            print(f"failed to record interaction log {message_id}: {exc}", file=sys.stderr, flush=True)

    def _valid_token(self, payload: dict[str, Any]) -> bool:
        expected = self.options.verification_token
        if not expected:
            return True
        actual = (payload.get("header") or {}).get("token") or payload.get("token")
        return actual == expected


class FeishuHandler(BaseHTTPRequestHandler):
    bridge: FeishuBrainBridge

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"ok": True})
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json({"error": "invalid json"}, status=400)
            return

        if self.path not in {"/feishu/events", "/"}:
            self._send_json({"error": "not found"}, status=404)
            return

        result = self.bridge.handle_payload(payload)
        status = 200 if result.get("ok", True) else 403
        self._send_json(result, status=status)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal Brain Feishu bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--mode", choices=["remember", "ask", "auto"], default="auto")
    parser.add_argument("--ask-prefix", default="?")
    parser.add_argument("--ack-message", default="小柴记住了。")
    parser.add_argument(
        "--working-reaction",
        default="OK",
        help="emoji_type reaction added immediately when a message is accepted; empty disables it",
    )
    parser.add_argument("--app-id-env", default="FEISHU_APP_ID")
    parser.add_argument("--app-secret-env", default="FEISHU_APP_SECRET")
    parser.add_argument("--verification-token-env", default="FEISHU_VERIFICATION_TOKEN")
    parser.add_argument("--dry-run", action="store_true", help="process events but do not call Feishu reply API")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    args = build_parser().parse_args(argv)

    app_id = require_secret_env(args.app_id_env)
    app_secret = require_secret_env(args.app_secret_env)
    verification_token = get_secret_env(args.verification_token_env)

    brain = PersonalBrain.from_config_file(args.config)
    client = FeishuClient(app_id=app_id, app_secret=app_secret)
    options = FeishuOptions(
        mode=args.mode,
        ask_prefix=args.ask_prefix,
        ack_message=args.ack_message,
        working_reaction=args.working_reaction or None,
        verification_token=verification_token,
        app_id=app_id,
        app_secret=app_secret,
        dry_run=args.dry_run,
    )
    FeishuHandler.bridge = FeishuBrainBridge(brain=brain, client=client, options=options)
    server = ThreadingHTTPServer((args.host, args.port), FeishuHandler)
    print(f"Feishu bridge listening on http://{args.host}:{args.port}/feishu/events", flush=True)
    print(f"mode={args.mode} ask_prefix={args.ask_prefix!r} dry_run={args.dry_run}", flush=True)
    server.serve_forever()
    return 0


def is_url_verification(payload: dict[str, Any]) -> bool:
    payload_type = payload.get("type") or (payload.get("header") or {}).get("type")
    return payload_type == "url_verification" and "challenge" in payload


def extract_text_message(message: dict[str, Any]) -> str:
    if message.get("message_type") != "text":
        return ""
    try:
        content = json.loads(str(message.get("content") or "{}"))
    except json.JSONDecodeError:
        return ""
    return str(content.get("text") or "").strip()


def extract_sender(event: dict[str, Any]) -> str:
    sender = event.get("sender") or {}
    sender_id = sender.get("sender_id") or {}
    for key in ("user_id", "open_id", "union_id"):
        value = sender_id.get(key)
        if value:
            return str(value)
    return "feishu"


def extract_question(text: str, ask_prefix: str) -> str | None:
    clean = text.strip()
    prefixes = [ask_prefix]
    if ask_prefix == "?":
        prefixes.append("？")
    for prefix in prefixes:
        if prefix and clean.startswith(prefix):
            question = clean[len(prefix) :].strip()
            return question or None
    return None


def format_remembered_reply(ack_message: str, details: list[MemoryDetail]) -> str:
    lines = [ack_message or "小柴记住了。"]
    if len(details) >= 4:
        lines.append(f"这句话被拆成了 {len(details)} 条记忆，后续可以复盘是否拆得过细。")
    for index, detail in enumerate(details, start=1):
        topics = "、".join(detail.summary.topics) if detail.summary.topics else "无主题"
        lines.extend(
            [
                "",
                f"{index}. 大类：{detail.summary.memory_category}",
                f"   主题：{topics}",
                f"   内容：{detail.summary.content}",
            ]
        )
    return "\n".join(lines)


def answer_evidence_payload(result: AnswerResult) -> list[dict[str, Any]]:
    return [
        {
            "memory_id": item.memory_id,
            "raw_message_id": item.recall.raw_message_id,
            "relevance": item.relevance,
            "title": item.recall.title,
            "memory_category": item.recall.memory_category,
        }
        for item in result.evidence
    ]


def request_json(
    url: str,
    method: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        request_headers.update(headers)
    last_error: Exception | None = None
    for attempt in range(1, 4):
        request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Feishu HTTP error {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, ssl.SSLError) as exc:
            last_error = exc
            if attempt == 3:
                raise RuntimeError(f"Feishu request failed after retries: {exc}") from exc
            time.sleep(0.8 * attempt)
    else:
        raise RuntimeError(f"Feishu request failed: {last_error}")
    code = data.get("code", 0)
    if code not in {0, "0"}:
        raise RuntimeError(f"Feishu API error: {data}")
    return data


def require_secret_env(name: str) -> str:
    value = get_secret_env(name)
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
