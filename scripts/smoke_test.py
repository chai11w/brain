from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from personal_brain import PersonalBrain


DEFAULT_TEST_TEXT = (
    "V0健康检查：小柴当前最重要的是稳定完成记忆写入、语义召回、"
    "基于证据回答和飞书入口使用体验。"
)
DEFAULT_QUESTION = "小柴当前最重要的稳定目标是什么？"


@dataclass
class StepResult:
    name: str
    ok: bool
    elapsed_ms: int
    detail: str


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Personal Brain V0 smoke test")
    parser.add_argument("--config", default="config.json", help="config file path")
    parser.add_argument(
        "--live-ingest",
        action="store_true",
        help="write one test raw_message and memory into the real database",
    )
    parser.add_argument("--text", default=DEFAULT_TEST_TEXT, help="test text for --live-ingest")
    parser.add_argument("--question", default=DEFAULT_QUESTION, help="recall/ask question")
    parser.add_argument("--recall-limit", type=int, default=5)
    parser.add_argument("--evidence-limit", type=int, default=4)
    args = parser.parse_args()

    brain = PersonalBrain.from_config_file(args.config)
    results: list[StepResult] = []
    ingested_memory_ids: list[int] = []

    results.append(run_step("init_db", lambda: format_init_db(brain)))
    results.append(run_step("stats", lambda: brain.stats()))
    results.append(run_step("test_chat", lambda: brain.test_chat("请用一句中文回复：模型已接通。")))

    if args.live_ingest:
        def ingest() -> str:
            result = brain.ingest(
                args.text,
                source="smoke_test",
                sender="codex",
                rebuild_router=True,
            )
            ingested_memory_ids.extend(result.memory_ids)
            return (
                f"raw_message_id={result.raw_message_id}; "
                f"memories={result.memory_ids}; "
                f"router_rebuilt={result.router_rebuilt}; "
                f"warning={result.warning}"
            )

        results.append(run_step("live_ingest", ingest))
    else:
        results.append(
            StepResult(
                name="live_ingest",
                ok=True,
                elapsed_ms=0,
                detail="skipped; pass --live-ingest to test write/extract/embed",
            )
        )

    results.append(run_step("embed_missing", lambda: format_embed(brain)))
    results.append(run_step("recall", lambda: format_recall(brain, args.question, args.recall_limit, ingested_memory_ids)))
    results.append(
        run_step(
            "ask",
            lambda: format_ask(brain, args.question, args.recall_limit, args.evidence_limit),
        )
    )
    results.append(run_step("build_router", lambda: format_router(brain)))

    print_report(results)
    return 0 if all(item.ok for item in results) else 1


def run_step(name: str, func) -> StepResult:
    started = time.perf_counter()
    try:
        detail = str(func()).strip()
        ok = True
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        ok = False
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return StepResult(name=name, ok=ok, elapsed_ms=elapsed_ms, detail=detail)


def format_init_db(brain: PersonalBrain) -> str:
    result = brain.init_db()
    return f"database={result.database_path}; schema_version={result.schema_version}"


def format_embed(brain: PersonalBrain) -> str:
    result = brain.embed_missing_memories(limit=100)
    return f"embedded={result.embedded_count}; skipped={result.skipped_count}; warning={result.warning}"


def format_recall(
    brain: PersonalBrain,
    question: str,
    limit: int,
    expected_memory_ids: list[int],
) -> str:
    results = brain.recall(question, limit=limit)
    if not results:
        raise RuntimeError("no recall results")
    top = results[0]
    expected = ""
    if expected_memory_ids:
        hit = any(item.memory_id in expected_memory_ids for item in results)
        if not hit:
            raise RuntimeError(f"live-ingest memories not found in recall: {expected_memory_ids}")
        expected = f"; live_ingest_hit={hit}"
    return f"top_memory_id={top.memory_id}; score={top.score:.4f}; title={top.title}{expected}"


def format_ask(
    brain: PersonalBrain,
    question: str,
    recall_limit: int,
    evidence_limit: int,
) -> str:
    result = brain.ask(
        question,
        recall_limit=recall_limit,
        evidence_limit=evidence_limit,
    )
    evidence_ids = [item.memory_id for item in result.evidence]
    if not result.answer.strip():
        raise RuntimeError("empty answer")
    if not evidence_ids:
        raise RuntimeError("answer has no evidence")
    one_line_answer = " ".join(result.answer.split())
    return f"evidence={evidence_ids}; answer={shorten(one_line_answer, 180)}"


def format_router(brain: PersonalBrain) -> str:
    result = brain.build_router()
    paths = [
        Path(result.brain_index_path),
        Path(result.topics_path),
        Path(result.manifest_path),
    ]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise RuntimeError(f"missing router files: {missing}")
    warning = "; ".join(result.warnings) if result.warnings else None
    return (
        f"topics={result.topic_count}; manifest={result.memory_count}; "
        f"warning={warning}"
    )


def print_report(results: list[StepResult]) -> None:
    print("# Personal Brain Smoke Test")
    print("")
    for item in results:
        status = "PASS" if item.ok else "FAIL"
        print(f"[{status}] {item.name} ({item.elapsed_ms} ms)")
        print(f"  {item.detail}")
    print("")
    failed = [item.name for item in results if not item.ok]
    if failed:
        print(f"result: failed steps: {', '.join(failed)}")
    else:
        print("result: all checks passed")


def shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
