from __future__ import annotations

import argparse
import sys

from personal_brain import PersonalBrain


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal Brain V0 Memory Router")
    parser.add_argument("--config", default="config.json", help="config file path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="initialize the AI-native database foundation")
    subparsers.add_parser("build-router", help="build brain_index.json and router manifests")
    subparsers.add_parser("stats", help="show local store stats")
    test_chat_parser = subparsers.add_parser("test-chat", help="test configured chat model")
    test_chat_parser.add_argument(
        "prompt",
        nargs="?",
        default="请用一句话回复：模型已接通。",
        help="test prompt",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    brain = PersonalBrain.from_config_file(args.config)

    if args.command == "init-db":
        result = brain.init_db()
        print(f"database: {result.database_path}")
        print(f"schema version: {result.schema_version}")
        print("tables:")
        for table, count in result.tables.items():
            print(f"- {table}: {count}")
        for warning in result.warnings:
            print(f"warning: {warning}")
        return 0

    if args.command == "build-router":
        result = brain.build_router()
        print(f"brain index: {result.brain_index_path}")
        print(f"topics: {result.topics_path} ({result.topic_count})")
        print(f"manifest: {result.manifest_path} ({result.memory_count})")
        for warning in result.warnings:
            print(f"warning: {warning}")
        return 0

    if args.command == "stats":
        print(brain.stats())
        return 0

    if args.command == "test-chat":
        print(brain.test_chat(args.prompt))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
