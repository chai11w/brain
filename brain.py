from __future__ import annotations

import argparse
import getpass
import sys

from personal_brain import PersonalBrain


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal Brain V0 Memory Router")
    parser.add_argument("--config", default="config.json", help="config file path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="initialize the AI-native database foundation")
    subparsers.add_parser("build-router", help="build brain_index.json and router manifests")
    subparsers.add_parser("stats", help="show local store stats")

    secure_add_parser = subparsers.add_parser("secure-add", help="add encrypted secure item")
    secure_add_parser.add_argument("--label", required=True, help="item label, for example GitHub main")
    secure_add_parser.add_argument("--type", default="password", help="secret type: password/api_key/token/note")
    secure_add_parser.add_argument("--username", help="optional username")
    secure_add_parser.add_argument("--note", help="optional non-secret note")

    subparsers.add_parser("secure-list", help="list secure item metadata without secrets")

    secure_get_parser = subparsers.add_parser("secure-get", help="decrypt one secure item")
    secure_get_parser.add_argument("label", help="item label")

    ingest_parser = subparsers.add_parser("ingest", help="extract AI atomic memories from input text")
    ingest_parser.add_argument("text", help="raw user input")
    ingest_parser.add_argument("--source", default="cli", help="message source")
    ingest_parser.add_argument("--sender", default="me", help="message sender")
    ingest_parser.add_argument(
        "--no-router",
        action="store_true",
        help="do not rebuild Memory Router after ingest",
    )

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

    if args.command == "ingest":
        result = brain.ingest(
            args.text,
            source=args.source,
            sender=args.sender,
            rebuild_router=not args.no_router,
        )
        print(f"raw_message_id: {result.raw_message_id}")
        print(f"extraction_run_id: {result.extraction_run_id}")
        print(f"should_remember: {result.should_remember}")
        print(f"memories: {result.memory_ids}")
        print(f"topics: {result.topic_ids}")
        print(f"entities: {result.entity_ids}")
        print(f"router_rebuilt: {result.router_rebuilt}")
        if result.warning:
            print(f"warning: {result.warning}")
        return 0

    if args.command == "stats":
        print(brain.stats())
        return 0

    if args.command == "secure-add":
        secret = getpass.getpass("secret: ")
        master_password = getpass.getpass("master password: ")
        item_id = brain.secure_add(
            label=args.label,
            secret_type=args.type,
            username=args.username,
            note=args.note,
            secret=secret,
            master_password=master_password,
        )
        print(f"secure item saved: {item_id}")
        print("secret was encrypted locally and was not sent to AI or Router")
        return 0

    if args.command == "secure-list":
        items = brain.secure_list()
        if not items:
            print("no secure items")
            return 0
        for item in items:
            username = f" username={item.username}" if item.username else ""
            note = f" note={item.note}" if item.note else ""
            print(f"#{item.id} {item.label} type={item.secret_type}{username}{note} updated={item.updated_at}")
        return 0

    if args.command == "secure-get":
        master_password = getpass.getpass("master password: ")
        item = brain.secure_get(args.label, master_password)
        print(f"label: {item.summary.label}")
        print(f"type: {item.summary.secret_type}")
        if item.summary.username:
            print(f"username: {item.summary.username}")
        print(f"secret: {item.secret}")
        return 0

    if args.command == "test-chat":
        print(brain.test_chat(args.prompt))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
