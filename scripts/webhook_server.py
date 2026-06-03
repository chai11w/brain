from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from personal_brain import PersonalBrain


class BrainWebhookHandler(BaseHTTPRequestHandler):
    brain: PersonalBrain

    def do_POST(self) -> None:
        if self.path != "/message":
            self._send_json({"error": "not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json({"error": "invalid json"}, status=400)
            return

        text = str(payload.get("text", "")).strip()
        sender = str(payload.get("sender", "me"))
        source = str(payload.get("source", "wechat"))
        reply = self.brain.handle_message(text, sender=sender, source=source)
        self._send_json({"reply": reply})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Personal Brain V0 webhook server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()

    BrainWebhookHandler.brain = PersonalBrain.from_config_file(args.config)
    server = ThreadingHTTPServer((args.host, args.port), BrainWebhookHandler)
    print(f"Personal Brain webhook listening on http://{args.host}:{args.port}/message")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

