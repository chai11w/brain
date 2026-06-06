# Project Memory: Xiaochai / AI-native Personal Brain

This is project-scoped handoff memory for Codex/AI agents working in this
repository. Do not treat it as global memory.

## User Goal

The user is building an AI-native Personal Brain / Xiaochai Memory Box, not a
note app, CRUD tool, keyword search system, or fixed folder taxonomy.

Target flow:

```text
casual input
-> preserve exact raw input
-> AI judges whether it is worth remembering
-> AI rewrites it into long-term atomic memories
-> topics/entities/category/importance/confidence are assigned
-> embeddings support semantic recall
-> answers cite retrieved evidence
```

The user wants Codex to act as a long-term technical partner and architecture
reviewer, not merely an executor.

## Working Style

- Explain in Chinese, plainly first, then point to files/code.
- Before implementing product/architecture changes, review whether the request
  solves the current bottleneck.
- Push back when a proposal is too CRUD-like, keyword-based, fixed-folder based,
  or premature for the current stage.
- For project rules/status/future plans, update `.agents/project_memory.md`;
  do not ingest them into Xiaochai's personal memory database.
- Never write real API keys, Feishu secrets, passwords, tokens, or local private
  database contents into tracked files.

## Current Project State

Repository:

- Workspace: `F:\cc\13khoj第二大脑-记忆`
- Branch: `codex-memory-archive-mvp`
- Remote: `origin https://github.com/chai11w/brain.git`
- Upload status: this handoff expects the latest local fixes to be committed and
  pushed to `origin/codex-memory-archive-mvp`. Verify with `git status --branch`
  and `git log -1`.

Implemented:

- SQLite source of truth: `data/personal_brain.sqlite3`
- Raw input preservation: `raw_messages`
- AI extraction audit: `memory_extraction_runs`
- AI-rewritten atomic memories: `memories`
- Dynamic topics/entities plus stable broad `memory_category`
- Embedding storage and semantic recall: `personal_brain/semantic.py`
- Evidence-constrained answering: `personal_brain/answer.py`
- Memory Router outputs: `brain_index.json`, `memory/topics.json`,
  `memory/memory_manifest.json`
- Secure vault: `personal_brain/vault.py`
- Feishu bridge MVP: `scripts/feishu_bridge.py`
- Feishu interaction audit: `interaction_logs`
- Xiaochai launcher/watchdog: `scripts/start_xiaochai.ps1`,
  `scripts/xiaochai_watchdog.ps1`
- Daily extraction report CLI: `personal_brain/daily_report.py`
- Codex App daily report automation at 10:00 for the previous 24 hours
- wxauto WeChat bridge shell exists but is not the preferred channel

Not implemented / deferred:

- Frontend
- Neo4j / knowledge graph visualization / GraphRAG
- Multi-database deployment
- Weekly reflective Markdown review automation
- Full embedding-based semantic write-time dedupe
- Read-time evidence dedupe

## Recent Fixes In Current Branch

These fixes were implemented during the latest stabilization pass. The local
bridge was restarted after the code changes, so runtime behavior should already
be active locally.

1. Feishu delayed retry protection
   - File: `scripts/feishu_bridge.py`
   - Adds persistent `message_id` dedupe via `interaction_logs`.
   - Ignores Feishu messages older than 15 minutes by default.
   - Stale events are logged as `stale_ignored`, not replied to, and not stored.

2. Write-time near-duplicate protection
   - File: `personal_brain/extractor.py`
   - Before inserting extracted memory candidates, compares them with recent
     active memories.
   - Skips very similar candidates while preserving raw messages and extraction
     runs for audit.
   - This is deterministic text/near-duplicate filtering, not full embedding
     semantic dedupe yet.

3. Question-shaped Xiaochai product feedback guard
   - File: `personal_brain/extractor.py`
   - If the model would ignore an input, but the text clearly discusses Xiaochai,
     the memory box, reports, Feishu, startup stability, retrieval, RAG, or
     embeddings as product feedback, preserve it as a project feedback memory.

4. Daily report Xiaochai review section
   - File: `personal_brain/daily_report.py`
   - Adds `小柴相关复盘分类`.
   - This is an extra deterministic index over the full report.
   - It does not remove or change the original full extraction details.
   - Categories: current defects, near-term fixes, future directions, other
     Xiaochai-related notes.

5. Documentation updates
   - Files: `README.md`, `.agents/project_memory.md`
   - README explains stale retry protection and the extra daily report section.
   - Project memory was cleaned into this current-state handoff.

Verification already run:

```powershell
python brain.py daily-report --last-hours 24
```

Latest verification report generated locally:

```text
reports/last-24h-2026-06-06-1039.md
```

Also verified with small Python checks:

- Chinese near-duplicate normalization works.
- Duplicate candidate matches an existing memory.
- Xiaochai question-shaped feedback is preserved.
- Daily report bucket classification returns current defects / near-term fixes /
  future directions for representative examples.

## Current Commands

General:

```powershell
python brain.py init-db
python brain.py stats
python brain.py test-chat "Reply in one short sentence: model connected."
python brain.py ingest "..."
python brain.py memory-list
python brain.py memory-show 1
python brain.py memory-archive 1
python brain.py embed-memories
python brain.py recall "..."
python brain.py ask "..."
python brain.py daily-report --last-hours 24
python brain.py build-router
```

Feishu bridge:

```powershell
python scripts\feishu_bridge.py --port 8787 --mode auto --ask-prefix "?"
```

Launcher/watchdog:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_xiaochai.ps1
```

Secure vault:

```powershell
python brain.py secure-add --label "..." --type password --username "..."
python brain.py secure-list
python brain.py secure-get "..."
```

## Runtime / Channel Notes

- Feishu is the preferred MVP interaction channel.
- Desktop WeChat automation is a backup shell only; do not resume unless the
  user explicitly asks.
- `启动小柴.bat` calls the launcher. The launcher starts a hidden watchdog that
  keeps the local Feishu bridge and cloudflared process alive and writes status
  to `.tmp_tests/xiaochai_status.txt`.
- The watchdog can restart local processes, but account-less `trycloudflare.com`
  quick tunnel URLs are not stable.
- Stable daily Feishu use requires a fixed public URL, preferably Cloudflare
  Named Tunnel configured through `XIAOCHAI_TUNNEL_NAME`,
  `XIAOCHAI_CLOUDFLARED_CONFIG`, and `XIAOCHAI_PUBLIC_HOST`.
- Current local bridge was restarted after the latest local fixes, so the new
  runtime behavior should already be active locally.

## Architecture Rules

Non-negotiable:

- Preserve raw user input in `raw_messages`.
- Store AI-rewritten atomic memories in `memories`.
- Retrieval should use embeddings/RAG as the primary recall path.
- Topics, entities, type, importance, and confidence must be AI-generated.
- Stable broad category guides navigation; it must not replace semantic recall.
- Answers must cite retrieved memory/raw-message evidence.
- Markdown/folders are exports or views, not the source of truth.
- Adapters such as Feishu/WeChat only receive/send messages and call the core
  brain. They must not duplicate extraction, embeddings, recall, or answer logic.
- Do not build frontend, Neo4j, GraphRAG, visualization, or a new database unless
  the user explicitly revisits that architecture decision.

## Current Memory Flow

Ingest:

```text
input text
-> raw_messages
-> AI structured extraction
-> Xiaochai product-feedback guard
-> write-time near-duplicate filter
-> memory_extraction_runs
-> memories
-> topic/entity links
-> embeddings for new memory IDs when enabled
-> rebuild Router
```

Ask:

```text
question
-> semantic recall
-> AI rerank of candidate evidence
-> answer only from selected evidence
-> cite memory_id and raw_message_id
```

## Known Risks / Watch Items

- Deterministic near-duplicate filtering may miss paraphrases with different
  wording. If real duplicates still leak through, add embedding-based semantic
  dedupe before insertion.
- Daily report Xiaochai classification is fixed-rule indexing. It is useful for
  review, but not a replacement for Codex reading the full report when the user
  asks for product interpretation.
- Temporary trycloudflare URLs can expire or change. Fixed domain/Named Tunnel
  remains the real stability solution.
- Existing files may contain mojibake from older Windows console output. When
  editing docs, prefer UTF-8 and verify Chinese text in the file, not only in
  PowerShell output.

## Documentation Roles

- `README.md`: usage and setup
- `项目地图.md`: Chinese user-facing overview
- `ARCHITECTURE.md`: architecture principles and review gates
- `.agents/project_memory.md`: current project handoff memory for future Codex

## Next Best Step

Continue the stabilization loop:

```text
use Xiaochai normally
-> daily 10:00 rolling 24h report is generated
-> user asks Codex to inspect reports when needed
-> fix extraction, recall, answer formatting, archive/correction, and startup issues
-> avoid large product features until the foundation feels stable
```

Later, after the foundation is stable:

- Add embedding-based write-time semantic dedupe if needed.
- Add read-time evidence dedupe.
- Add periodic storage-library quality review.
- Revisit weekly reflective Markdown review automation.
- Revisit Query Planning RAG and more capable Xiaochai robot behavior.
