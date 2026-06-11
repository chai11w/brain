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
- When Codex changes Xiaochai based on a daily report review, also update
  `.agents/stabilization_log.md` with the problem, change, and later
  verification method/status.
- Keep project Markdown files maintained, not merely appended to. Remove,
  compress, or archive stale details when a fix is verified and no longer useful
  for future decisions.
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
- Manual Xiaochai backlog review: `.agents/xiaochai_backlog.md`
- Project Skill for scoped Xiaochai report review:
  `.agents/skills/xiaochai-daily-review-c/SKILL.md`
- wxauto WeChat bridge shell exists but is not the preferred channel

Not implemented / deferred:

- Frontend
- Neo4j / knowledge graph visualization / GraphRAG
- Multi-database deployment
- Weekly Memory Compression review implementation
- Stable `学习` category for compact concept notes
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

4. Daily report Xiaochai review section disabled
   - File: `personal_brain/daily_report.py`
   - The previous deterministic `小柴相关复盘分类` section was removed because
     it was too broad and could misclassify general AI notes as Xiaochai work.
   - Daily reports now stay closer to audit evidence: issue markers, raw input,
     stored memories, extraction runs, memory details, and interactions.
   - Product interpretation should be done manually with Codex and recorded in
     `.agents/xiaochai_backlog.md` when it affects future work.

5. Same-day todo recall
   - Files: `personal_brain/semantic.py`, `personal_brain/answer.py`
   - Xiaochai now boosts `临时待办` and task-like memories for questions such as
     `今天要做什么`.
   - The answer layer receives the current date and guidance for resolving
     relative dates such as yesterday's `明天`.
   - Verified locally: `python -B brain.py recall "今天要做什么" --limit 5`
     ranks `临时待办` memories first; the local Feishu bridge was restarted.

6. Documentation and review workflow updates
   - Files: `README.md`, `.agents/project_memory.md`,
     `.agents/stabilization_log.md`, `.agents/xiaochai_backlog.md`
   - Project memory and stabilization/backlog docs track current behavior,
     decisions, and future review items.
   - Added project Skill `xiaochai-daily-review-c` for scoped report/database
     reviews without broad project onboarding.

Verification already run:

```powershell
python brain.py daily-report --last-hours 24
```

Latest reviewed daily reports:

```text
reports/last-24h-2026-06-09-1015.md
reports/last-24h-2026-06-10-1002.md
reports/last-24h-2026-06-11-1001.md
```

Recent review conclusions:

- 2026-06-10 report verifies the daily report no longer emits the automatic
  `小柴相关复盘分类` section.
- 2026-06-11 report shows raw `156`
  (`memory+recall就是储存加调取的组合`) was ignored. This is useful evidence for
  adding a stable `学习` category and preserving compact concept-definition
  notes.
- 2026-06-11 report also provides near-term evidence for a small weekly Memory
  Compression review: weekly/monthly reports should compress short-term memory
  into durable long-term memories, not merely display a Markdown digest.

Earlier small Python checks:

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
- Daily reports intentionally no longer auto-classify Xiaochai-related product
  items. Codex should read the raw report/database and update
  `.agents/xiaochai_backlog.md` when product interpretation matters.
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
- `.agents/stabilization_log.md`: daily stabilization changes, known fix
  outcomes, and later verification status
- `.agents/xiaochai_backlog.md`: manually maintained product backlog and
  decision table for Xiaochai-related memories

## Next Best Step

Continue the stabilization loop:

```text
use Xiaochai normally
-> daily 10:00 rolling 24h report is generated
-> user asks Codex to inspect reports when needed
-> use Skill xiaochai-daily-review-c for scoped report/database review
-> update .agents/xiaochai_backlog.md when Xiaochai-related items are reclassified
-> fix extraction, recall, answer formatting, archive/correction, and startup issues only when evidence shows a real failure
-> avoid large product features until the foundation feels stable
```

Later, after the foundation is stable:

- Add embedding-based write-time semantic dedupe if needed.
- Add read-time evidence dedupe.
- Verify same-day todo recall through Feishu real use; add lightweight
  completion/expiry handling only if stale todos become a real problem.
- Add a stable `学习` category if implementing the current backlog design:
  use it for reusable short concept notes, definitions, distinctions, analogies,
  and "I learned X means Y" records. Raw `156`
  (`memory+recall就是储存加调取的组合`) should be remembered under this boundary,
  while technical judgments stay in `技术思考`, process patterns stay in
  `工作流方法`, and direct Xiaochai changes stay in `现有项目改进`.
- Design one small weekly Memory Compression review before building automation:
  group recent memories by broad category, identify short-term memories at risk
  of going stale, and propose durable summary memories for review.
- Add periodic storage-library quality review.
- Revisit Query Planning RAG and more capable Xiaochai robot behavior.
