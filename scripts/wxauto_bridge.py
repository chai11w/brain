from __future__ import annotations

import argparse
import os
import sys
import threading
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from personal_brain import PersonalBrain  # noqa: E402


@dataclass(frozen=True)
class BridgeOptions:
    mode: str
    ask_prefix: str
    ack_message: str
    include_self: bool
    dry_run: bool


class WxautoBrainBridge:
    """Minimal wxauto shell around PersonalBrain.

    WeChat automation stays at the edge. Memory extraction, retrieval, and
    answering remain inside PersonalBrain.
    """

    def __init__(self, brain: PersonalBrain, options: BridgeOptions):
        self.brain = brain
        self.options = options
        self._lock = threading.Lock()

    def handle_incoming(self, msg: Any, chat: Any) -> None:
        if not should_process_message(msg, include_self=self.options.include_self):
            return

        text = clean_text(getattr(msg, "content", ""))
        if not text:
            return

        sender = clean_text(getattr(msg, "sender", "")) or clean_text(str(chat)) or "wechat"
        print(f"received from {sender}: {text}", flush=True)

        with self._lock:
            try:
                reply = self._reply_for_text(text, sender)
            except Exception as exc:
                reply = f"暂时处理失败：{exc}"

        if self.options.dry_run:
            print(f"dry-run reply: {reply}", flush=True)
            return

        chat.SendMsg(reply)
        print(f"replied to {sender}: {reply}", flush=True)

    def _reply_for_text(self, text: str, sender: str) -> str:
        if self.options.mode == "remember":
            return self._remember_text(text, sender)
        if self.options.mode == "ask":
            return self.brain.ask(text).answer
        if self.options.mode == "auto":
            prefix = self.options.ask_prefix
            if prefix and text.startswith(prefix):
                question = text[len(prefix) :].strip()
                if question:
                    return self.brain.ask(question).answer
            return self._remember_text(text, sender)
        raise ValueError(f"unsupported mode: {self.options.mode}")

    def _remember_text(self, text: str, sender: str) -> str:
        reply = self.brain.handle_message(text, sender=sender, source="wechat")
        if reply in {"已记住。", "已收到。"} and self.options.ack_message:
            return self.options.ack_message
        return reply


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal Brain wxauto bridge")
    parser.add_argument("--config", default="config.json", help="config file path")
    parser.add_argument(
        "--chat",
        action="append",
        required=True,
        help="WeChat chat name to listen to; repeat for multiple chats",
    )
    parser.add_argument(
        "--mode",
        choices=["remember", "ask", "auto"],
        default="remember",
        help="remember stores messages; ask answers every message; auto uses ask-prefix for questions",
    )
    parser.add_argument(
        "--ask-prefix",
        default="?",
        help="in auto mode, messages starting with this prefix are answered instead of stored",
    )
    parser.add_argument(
        "--ack-message",
        default="小柴记住了。",
        help="friendly reply after a message is stored successfully",
    )
    parser.add_argument(
        "--include-self",
        action="store_true",
        help="also process messages sent by the logged-in WeChat account",
    )
    parser.add_argument("--dry-run", action="store_true", help="print replies without sending them")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    args = build_parser().parse_args(argv)
    WeChat = import_wechat()

    brain = PersonalBrain.from_config_file(args.config)
    bridge = WxautoBrainBridge(
        brain=brain,
        options=BridgeOptions(
            mode=args.mode,
            ask_prefix=args.ask_prefix,
            ack_message=args.ack_message,
            include_self=args.include_self,
            dry_run=args.dry_run,
        ),
    )

    wx = WeChat()
    for chat_name in args.chat:
        wx.AddListenChat(chat_name, bridge.handle_incoming)
        print(f"listening: {chat_name}", flush=True)
    print("wxauto bridge is running. Press Ctrl+C to stop.", flush=True)
    wx.KeepRunning()
    return 0


def import_wechat() -> Any:
    prepare_comtypes_cache()
    try:
        from wxauto4 import WeChat

        return WeChat
    except ImportError as exc:
        raise SystemExit(
            "wxauto4 is not installed. Install it with: pip install wxauto4"
        ) from exc


def prepare_comtypes_cache() -> None:
    cache_dir = PROJECT_ROOT / ".tmp_comtypes_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        import comtypes
    except ImportError:
        return

    module = sys.modules.get("comtypes.gen")
    if module is None:
        module = types.ModuleType("comtypes.gen")
        sys.modules["comtypes.gen"] = module
    module.__path__ = [os.fspath(cache_dir)]
    comtypes.gen = module


def should_process_message(msg: Any, include_self: bool = False) -> bool:
    attr = str(getattr(msg, "attr", "")).lower()
    if attr == "self" and not include_self:
        return False
    msg_type = str(getattr(msg, "type", "")).lower()
    if msg_type in {"time", "system"}:
        return False
    return True


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
