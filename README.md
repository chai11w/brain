# Personal Brain V0

AI-native Personal Brain is a local-first memory system.

It is not a note app, keyword search tool, fixed folder taxonomy, knowledge
graph demo, or frontend project.

Current flow:

```text
Feishu / WeChat / CLI message
-> raw_messages keeps the exact input
-> AI extracts atomic memories
-> topics / entities are identified dynamically
-> embeddings are generated when configured
-> Memory Router is rebuilt
-> recall / ask answers from evidence
```

## Current Scope

Implemented:

- SQLite source of truth
- AI memory extraction
- atomic `memories`
- dynamic `topics` and `entities`
- stable `memory_category` on each memory for broad navigation
- embedding-backed semantic recall
- evidence-constrained `ask`
- Memory Router files for Codex/AI navigation
- local encrypted secure vault
- Feishu bridge MVP
- Feishu interaction logs for answer/reply review
- local daily Markdown extraction reports
- Codex App daily report extraction automation
- wxauto WeChat bridge shell

Not implemented:

- weekly Memory Compression review implementation
- stable `学习` category for compact concept notes
- frontend
- knowledge graph visualization
- Neo4j
- GraphRAG
- multi-database deployment

## Core Rules

- Preserve raw input in `raw_messages`.
- Store AI-rewritten atomic memories in `memories`.
- Use embeddings/RAG as the primary recall path.
- Let AI identify topics, entities, type, importance, and confidence.
- Use stable broad categories for navigation, while keeping topics dynamic.
- Answers must cite memory/raw-message evidence.
- Markdown is an export/view layer, not the source of truth.
- Secrets must go to the secure vault, not to normal memory.

## Setup

Copy `config.example.json` to `config.json`, then set API keys through
environment variables. Do not put real secrets in tracked files.

Example for the Z.AI key in the current PowerShell session:

```powershell
$env:ZAI_API_KEY="your real key"
```

For persistent user-level variables:

```powershell
[Environment]::SetEnvironmentVariable("ZAI_API_KEY", "your real key", "User")
```

Restart PowerShell after setting user-level variables, or load them into the
current session manually.

## Common Commands

Initialize or inspect the database:

```powershell
python brain.py init-db
python brain.py stats
```

Test the chat model:

```powershell
python brain.py test-chat "Reply in one short sentence: model connected."
```

Ingest a thought:

```powershell
python brain.py ingest "I want Personal Brain to be AI-native, not just keyword search."
```

Review extracted memories:

```powershell
python brain.py memory-list
python brain.py memory-show 1
python brain.py memory-archive 1
```

Review recent channel interactions:

```powershell
python brain.py interaction-list
```

Generate a local daily extraction report:

```powershell
python brain.py daily-report --date today
python brain.py daily-report --date 2026-06-05
python brain.py daily-report --last-hours 24
```

Reports are written to `reports/YYYY-MM-DD.md`. This version extracts same-day
records and adds deterministic issue markers for the memory pipeline, including
raw message status, extraction failures, stored memory formatting, interaction
errors, and old reply citation formats. It does not call AI, edit memories, or
read or repair reports. The `reports/` directory is git-ignored because reports
contain raw user text, extracted memories, replies, errors, and evidence.

Reports intentionally do not auto-classify Xiaochai-related product items.
The report should stay close to audit evidence: raw input, extraction status,
stored memories, interaction logs, and deterministic issue markers. When product
interpretation is needed, review the report/database with Codex and maintain the
manual backlog in `.agents/xiaochai_backlog.md`.

Run the same extraction from a script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_daily_report.ps1
```

Backup only: install a Windows scheduled task for daily extraction at 10:00:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_daily_report_task.ps1
```

The active automation is the Codex App automation named `小柴每日报告提取`,
scheduled at 10:00 to run the previous 24 hours. The Windows scheduled task
installer is only a backup option and is not expected to be active by default.
Both paths only call the report extraction command. They do not call AI, read
reports, diagnose, edit data, or repair anything.

Daily product interpretation is handled by Codex through the project skill
`.agents/skills/xiaochai-daily-review-c/SKILL.md`. That review reads the report
and related database rows, extracts Xiaochai improvement/problem/experience
items, and proposes a small foundation-improvement plan when Xiaochai-related
evidence exists.

Run a quick V0 smoke test without writing new memories:

```powershell
python scripts/smoke_test.py
```

Run the full smoke test, including one real test ingest into the database:

```powershell
python scripts/smoke_test.py --live-ingest
```

Generate missing embeddings:

```powershell
python brain.py embed-memories
```

Recall relevant memories:

```powershell
python brain.py recall "AI-native Personal Brain architecture"
```

Ask from evidence:

```powershell
python brain.py ask "What did I previously decide about Personal Brain architecture?"
```

Build the Memory Router:

```powershell
python brain.py build-router
```

## What Ingest Does

`ingest` is the memory formation path:

```text
input text
-> raw_messages
-> memory_extraction_runs
-> memories
-> stable memory_category + dynamic topics / entities
-> memory_embeddings when embedding_model.enabled is true
-> brain_index.json / memory manifests
```

If embedding is enabled, new memories are embedded inside the core ingest flow.
Adapters such as Feishu and WeChat should not implement their own memory or
embedding logic.

## Memory Router

Generated files:

- `brain_index.json`
- `memory/topics.json`
- `memory/memory_manifest.json`

Codex and other AI callers should read in this order:

```text
brain_index.json
-> memory/topics.json
-> memory/memory_manifest.json
-> SQLite only for exact evidence
```

The router is a lightweight navigation layer. It is not RAG itself.

## Feishu Bridge

Feishu is the preferred MVP interaction channel.

Run locally:

```powershell
python scripts/feishu_bridge.py --port 8787 --mode auto --ask-prefix "?"
```

Modes:

- `remember`: store every text message as memory.
- `ask`: answer every text message from memory evidence.
- `auto`: messages starting with `?` are answered; other text is remembered.

Feishu shortcut commands in `auto` mode:

- Send normal text to remember it.
- Send `?question` or `？问题` to ask from memory evidence.
- Send `#42` to show memory 42 with its raw input and extraction metadata.
- Send `-42` to archive memory 42.
- Send `!` to show shortcut help.
- Archived memories no longer appear in semantic recall or Router manifests.
- Raw messages and extraction audit records are retained for review/recovery.

Shortcut commands intentionally use symbols instead of Chinese command words,
so normal notes that start with words like `详情` or `删除` can still be stored.

The bridge also writes `interaction_logs` so Codex can later review what the
user sent, whether the bridge remembered or answered, what it replied, which
evidence was used, and whether a model/API error occurred.

To avoid delayed Feishu retries becoming duplicate memories, the bridge ignores
already-seen `message_id` values from `interaction_logs` and skips Feishu
messages older than `--max-message-age-minutes` minutes. The default is 15
minutes, and stale messages are logged with action `stale_ignored` but are not
replied to or stored as memories.

Memory acknowledgement replies include the broad memory category and dynamic
topics for each extracted memory. If one message is split into many memories,
the reply warns that the split may need review.

Required environment variables:

```powershell
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_VERIFICATION_TOKEN
```

Feishu app setup:

1. Create a custom app in Feishu Open Platform.
2. Enable Bot capability.
3. Add the bot to the target chat or group.
4. Grant receive-message and reply/send-message permissions.
5. Subscribe to `im.message.receive_v1`.
6. Configure the event request URL to your public tunnel:

```text
https://your-public-domain/feishu/events
```

7. Leave Encrypt Key empty for MVP. The bridge supports verification token, not
   encrypted event payloads yet.

Local tunnel example:

```powershell
cloudflared tunnel --url http://127.0.0.1:8787
```

The desktop launcher `启动小柴.bat` starts a background watchdog through
`scripts/start_xiaochai.ps1`. The watchdog keeps the local Feishu bridge and
cloudflared process running and writes status to:

```text
.tmp_tests/xiaochai_status.txt
```

The latest Feishu event URL is shown in the `Xiaochai Status` monitor window
and `.tmp_tests/xiaochai_status.txt`.

If no fixed tunnel is configured, it falls back to a temporary
`trycloudflare.com` tunnel. This is only a backup: temporary URLs can change
when the tunnel restarts, so Feishu may still point to an expired URL.

For stable daily use, configure a Cloudflare Named Tunnel or another fixed
public domain, then set user-level environment variables before launching:

```powershell
[Environment]::SetEnvironmentVariable("XIAOCHAI_TUNNEL_NAME", "your-tunnel-name", "User")
[Environment]::SetEnvironmentVariable("XIAOCHAI_CLOUDFLARED_CONFIG", "C:\Users\you\.cloudflared\config.yml", "User")
[Environment]::SetEnvironmentVariable("XIAOCHAI_PUBLIC_HOST", "xiaochai.your-domain.com", "User")
```

Then set Feishu event subscription to:

```text
https://xiaochai.your-domain.com/feishu/events
```

Health check:

```text
http://127.0.0.1:8787/health
```

## WeChat Bridge

The wxauto bridge is a backup shell for Windows desktop WeChat.

```powershell
python scripts/wxauto_bridge.py --chat "Your memory inbox chat" --mode auto --ask-prefix "?"
```

The bridge should only receive/send messages and call `PersonalBrain`.
Core memory logic stays in `personal_brain`.

## Secure Vault

Secrets are not normal memories. Passwords, API keys, tokens, and private notes
must not go through AI extraction, Router manifests, embeddings, or Markdown
exports.

Commands:

```powershell
python brain.py secure-add --label "GitHub main" --type password --username chai11w
python brain.py secure-list
python brain.py secure-get "GitHub main"
```

`secure-add` and `secure-get` ask for a master password. V0 uses Windows DPAPI
plus master-password-derived entropy. The database stores encrypted values only.

## File Map

- `brain.py`: CLI entrypoint
- `personal_brain/schema.py`: SQLite schema
- `personal_brain/extractor.py`: AI memory extraction
- `personal_brain/semantic.py`: embeddings and semantic recall
- `personal_brain/answer.py`: evidence-constrained answering
- `personal_brain/router.py`: Memory Router builder
- `personal_brain/vault.py`: encrypted secure vault
- `scripts/feishu_bridge.py`: Feishu bot bridge
- `scripts/wxauto_bridge.py`: WeChat shell
- `项目地图.md`: Chinese project overview for the user
- `ARCHITECTURE.md`: architecture principles
- `.agents/project_memory.md`: project-scoped handoff memory for Codex
- `.agents/xiaochai_backlog.md`: Xiaochai product backlog and decision table
- `.agents/stabilization_log.md`: stabilization changes and verification status
- `.agents/skills/xiaochai-daily-review-c/SKILL.md`: scoped daily report review workflow

## Next Best Step

The next product step is not a new database or knowledge graph.

The next useful step is to keep the stabilization loop running while designing
two small foundation improvements from real report evidence:

```text
daily 10:00 rolling 24h extraction report
-> user asks Codex to inspect reports when needed
-> use xiaochai-daily-review-c to extract Xiaochai issues/improvements
-> update .agents/xiaochai_backlog.md and .agents/stabilization_log.md
-> fix extraction, recall, answer formatting, archive/correction, and startup issues only when evidence shows a real failure
```

Near-term design items:

- Add a stable `学习` category if the current backlog boundary is accepted:
  compact concept notes, definitions, distinctions, analogies, and "I learned X
  means Y" records should be preserved for future review. Technical judgments
  still belong in `技术思考`, process patterns in `工作流方法`, and direct Xiaochai
  changes in `现有项目改进`.
- Design a small weekly Memory Compression review before building automation:
  group recent memories by broad category, find short-term memories at risk of
  going stale, and propose durable summary memories for review before writing
  anything back.

Future product direction currently captured from user notes:

- improve active judgment: what to remember, what to ignore, when to ask back
- support message withdrawal/correction across raw messages, memories,
  embeddings, Router, and interaction logs
- keep Xiaochai replies and generated topics in Chinese by default
- organize memories by broad category first, then dynamic topics
- use weekly Memory Compression review as a quality feedback loop
- add a memory lifecycle later: recent/frequent memories stay sharp, old
  low-value memories decay in recall weight, similar memories can merge into
  summaries, and outdated memories can become archived or superseded while raw
  evidence stays preserved
- add image memory later through a media evidence layer: preserve original image
  files or Feishu file references, store OCR/caption metadata, screen for
  sensitive content, then pass the derived description into normal memory
  extraction
- later explore relationship memory, decision style memory, digital twin
  behavior, and external app integration such as WeChat
