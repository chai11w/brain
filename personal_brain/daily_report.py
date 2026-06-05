from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .schema import BrainSchema


@dataclass(frozen=True)
class DailyReportResult:
    report_date: date
    output_path: Path
    markdown: str
    counts: dict[str, int]


class DailyReportBuilder:
    """Builds a local daily extraction report."""

    def __init__(self, schema: BrainSchema):
        self.schema = schema

    def build(self, report_date: date, output_dir: Path) -> DailyReportResult:
        self.schema.initialize()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{report_date.isoformat()}.md"
        with self.schema.connect() as conn:
            data = load_daily_data(conn, report_date)
        markdown = format_daily_report(report_date, data)
        output_path.write_text(markdown + "\n", encoding="utf-8")
        return DailyReportResult(
            report_date=report_date,
            output_path=output_path,
            markdown=markdown,
            counts={
                "raw_messages": len(data["raw_messages"]),
                "extraction_runs": len(data["extraction_runs"]),
                "memories": len(data["memories"]),
                "interactions": len(data["interactions"]),
            },
        )


def parse_report_date(value: str | None) -> date:
    if not value or value == "today":
        return date.today()
    if value == "yesterday":
        return date.today() - timedelta(days=1)
    return datetime.strptime(value, "%Y-%m-%d").date()


def load_daily_data(conn: sqlite3.Connection, report_date: date) -> dict[str, list[dict[str, Any]]]:
    start = report_date.isoformat()
    end = (report_date + timedelta(days=1)).isoformat()
    return {
        "raw_messages": fetch_rows(
            conn,
            """
            SELECT id, created_at, processed_at, source, sender, processed_status,
                   content, metadata_json
            FROM raw_messages
            WHERE created_at >= ? AND created_at < ?
            ORDER BY created_at, id
            """,
            (start, end),
        ),
        "extraction_runs": fetch_rows(
            conn,
            """
            SELECT id, raw_message_id, created_at, model_provider, model_name,
                   prompt_version, status, error, output_json
            FROM memory_extraction_runs
            WHERE created_at >= ? AND created_at < ?
            ORDER BY created_at, id
            """,
            (start, end),
        ),
        "memories": fetch_rows(
            conn,
            """
            SELECT id, raw_message_id, extraction_run_id, created_at, updated_at,
                   title, memory_category, memory_type, importance, confidence,
                   status, content
            FROM memories
            WHERE (created_at >= ? AND created_at < ?)
               OR (updated_at >= ? AND updated_at < ?)
            ORDER BY created_at, id
            """,
            (start, end, start, end),
        ),
        "interactions": fetch_rows(
            conn,
            """
            SELECT id, message_id, created_at, source, sender, mode, action,
                   status, raw_message_id, latency_ms, user_text, reply_text,
                   evidence_json, error
            FROM interaction_logs
            WHERE created_at >= ? AND created_at < ?
            ORDER BY created_at, id
            """,
            (start, end),
        ),
    }


def fetch_rows(conn: sqlite3.Connection, query: str, params: tuple[str, ...]) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def format_daily_report(report_date: date, data: dict[str, list[dict[str, Any]]]) -> str:
    lines = [
        f"# Personal Brain Daily Audit {report_date.isoformat()}",
        "",
        "Purpose: extract same-day records only. It does not call AI or modify data.",
        "Context: future Codex should read .agents/project_memory.md before interpreting this report.",
        "Privacy: this report may contain raw user text and should stay local.",
        "",
        "## Counts",
        "",
        f"- raw_messages: {len(data['raw_messages'])}",
        f"- extraction_runs: {len(data['extraction_runs'])}",
        f"- memories_created_or_updated: {len(data['memories'])}",
        f"- interactions: {len(data['interactions'])}",
    ]

    lines.extend(["", "## Raw Messages", ""])
    append_raw_messages(lines, data["raw_messages"])
    lines.extend(["", "## Extraction Runs", ""])
    append_extraction_runs(lines, data["extraction_runs"])
    lines.extend(["", "## Memories", ""])
    append_memories(lines, data["memories"])
    lines.extend(["", "## Interactions", ""])
    append_interactions(lines, data["interactions"])
    return "\n".join(lines).rstrip()


def append_raw_messages(lines: list[str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        lines.append("- none")
        return
    for row in rows:
        lines.extend(
            [
                f"### raw_message {row['id']}",
                "",
                f"- created_at: {row['created_at']}",
                f"- processed_at: {row['processed_at'] or ''}",
                f"- source: {row['source']}",
                f"- sender: {row['sender']}",
                f"- processed_status: {row['processed_status']}",
                f"- metadata_json: {row['metadata_json'] or ''}",
                "",
                fenced(row["content"]),
                "",
            ]
        )


def append_extraction_runs(lines: list[str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        lines.append("- none")
        return
    for row in rows:
        lines.extend(
            [
                f"### extraction_run {row['id']} / raw_message {row['raw_message_id']}",
                "",
                f"- created_at: {row['created_at']}",
                f"- model: {row['model_provider']} / {row['model_name']}",
                f"- prompt_version: {row['prompt_version']}",
                f"- status: {row['status']}",
                f"- error: {row['error'] or ''}",
                f"- output_summary: {summarize_extraction_output(row['output_json'])}",
                "",
                "Output JSON:",
                "",
                fenced(row["output_json"]),
                "",
            ]
        )


def append_memories(lines: list[str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        lines.append("- none")
        return
    for row in rows:
        lines.extend(
            [
                f"### memory {row['id']} / raw_message {row['raw_message_id']}",
                "",
                f"- extraction_run_id: {row['extraction_run_id']}",
                f"- created_at: {row['created_at']}",
                f"- updated_at: {row['updated_at']}",
                f"- status: {row['status']}",
                f"- title: {row['title'] or ''}",
                f"- category: {row['memory_category']}",
                f"- type: {row['memory_type']}",
                f"- importance: {row['importance']}",
                f"- confidence: {row['confidence']}",
                "",
                fenced(row["content"]),
                "",
            ]
        )


def append_interactions(lines: list[str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        lines.append("- none")
        return
    for row in rows:
        evidence = summarize_evidence(row["evidence_json"])
        lines.extend(
            [
                f"### interaction {row['id']}",
                "",
                f"- created_at: {row['created_at']}",
                f"- source: {row['source']}",
                f"- sender: {row['sender']}",
                f"- mode/action/status: {row['mode']} / {row['action']} / {row['status']}",
                f"- message_id: {row['message_id'] or ''}",
                f"- raw_message_id: {row['raw_message_id'] or ''}",
                f"- latency_ms: {row['latency_ms'] or ''}",
                f"- error: {row['error'] or ''}",
                f"- evidence: {evidence}",
                "",
                "User text:",
                "",
                fenced(row["user_text"]),
                "",
                "Reply text:",
                "",
                fenced(row["reply_text"] or ""),
                "",
                "Evidence JSON:",
                "",
                fenced(row["evidence_json"] or ""),
                "",
            ]
        )


def summarize_extraction_output(output_json: str) -> str:
    try:
        payload = json.loads(output_json)
    except json.JSONDecodeError:
        return "invalid JSON"
    memories = payload.get("atomic_memories")
    if not isinstance(memories, list):
        return "atomic_memories missing or not a list"
    titles = [str(item.get("title") or "untitled") for item in memories if isinstance(item, dict)]
    if not titles:
        return "0 memories"
    return f"{len(titles)} memories: " + "; ".join(titles)


def summarize_evidence(evidence_json: str | None) -> str:
    if not evidence_json:
        return ""
    try:
        evidence = json.loads(evidence_json)
    except json.JSONDecodeError:
        return "invalid JSON"
    if not isinstance(evidence, list):
        return "not a list"
    chunks = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        memory_id = item.get("memory_id")
        raw_message_id = item.get("raw_message_id")
        relevance = item.get("relevance")
        chunks.append(f"memory {memory_id}/raw {raw_message_id}/rel {relevance}")
    return "; ".join(chunks)


def fenced(text: str) -> str:
    fence = "```"
    if "```" in text:
        fence = "````"
    return f"{fence}\n{text}\n{fence}"
