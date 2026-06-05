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
- wxauto WeChat bridge shell

Not implemented:

- scheduled daily report automation
- weekly reflective review automation
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
```

Reports are written to `reports/YYYY-MM-DD.md`. This version extracts same-day
records and adds deterministic issue markers for the memory pipeline, including
raw message status, extraction failures, stored memory formatting, interaction
errors, and old reply citation formats. It does not call AI, edit memories, or
perform scheduled automation. The `reports/` directory is git-ignored because
reports contain raw user text, extracted memories, replies, errors, and
evidence.

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

Memory correction MVP:

- Send `删除 42`, `作废 42`, `撤回 42`, or `归档 42` in Feishu to archive
  that memory ID.
- Archived memories no longer appear in semantic recall or Router manifests.
- Raw messages and extraction audit records are retained for review/recovery.

The bridge also writes `interaction_logs` so Codex can later review what the
user sent, whether the bridge remembered or answered, what it replied, which
evidence was used, and whether a model/API error occurred.

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

## Next Best Step

The next product step is not a new database or knowledge graph.

The next useful step is a smoke test and Feishu stabilization pass:

```text
ingest
-> embed
-> recall
-> ask
-> Feishu remember/ask loop
```

After that, implement weekly Markdown review automation:

```text
Codex reads Router + recent memories
-> updates Markdown topics
-> extracts insights
```

Future product direction currently captured from user notes:

- improve active judgment: what to remember, what to ignore, when to ask back
- support message withdrawal/correction across raw messages, memories,
  embeddings, Router, and interaction logs
- keep Xiaochai replies and generated topics in Chinese by default
- organize memories by broad category first, then dynamic topics
- use weekly Codex review as a quality feedback loop
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
