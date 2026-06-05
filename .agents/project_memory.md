# Project Memory: AI-native Personal Brain

This is project-scoped handoff memory for Codex/AI agents working in this
repository. Do not treat it as global memory.

## User Goal

The user is building an AI-native Personal Brain, not a simple note app, CRUD
tool, keyword search system, or fixed folder taxonomy.

Product goal:

```text
casual input
-> AI understands, rewrites, and structures it
-> long-term atomic memories are formed
-> semantic retrieval finds relevant evidence
-> AI reasons over retrieved evidence and answers
```

The user wants Codex to act as a technical partner and architecture reviewer,
not merely an executor.

## Working Style

Before implementing a request:

1. Check whether it fits the AI-native Personal Brain goal.
2. Push back if the proposed path is too CRUD-like, keyword-based, or fixed-folder based.
3. Propose the better architecture.
4. Then decide whether to change code.

Before accepting any new feature proposal, Codex must explicitly review:

1. What problem is the user really trying to solve?
2. What is the current project's biggest bottleneck?
3. Does this feature solve that biggest bottleneck?
4. If not, clearly push back instead of simply implementing it.

The user is not deeply technical and prefers Chinese explanations with context.
When explaining architecture, database schema, Router, RAG, embeddings, or AI
pipelines, explain plainly first, then point to files/code.

Project-memory boundary:

- In project collaboration context, when the user says to "write it into memory"
  about workflow rules, CLI/GitHub upload habits, project status, or future
  implementation plans, write/update `.agents/project_memory.md` rather than
  ingesting it into Xiaochai's personal memory database.
- After CLI/GitHub upload work, include a short Chinese summary explaining what
  was changed, which CLI usage changed, what was pushed, and where to find it,
  so the user can quickly trace the work later.

## Current Project State

Implemented:

- SQLite source of truth in `data/personal_brain.sqlite3`
- AI-native schema in `personal_brain/schema.py`
- raw input preservation in `raw_messages`
- AI extraction audit in `memory_extraction_runs`
- AI-rewritten atomic memories in `memories`
- dynamic AI topics/entities
- stable broad `memory_category` on each memory for navigation
- embedding storage in `memory_embeddings`
- semantic recall in `personal_brain/semantic.py`
- evidence-constrained answer layer in `personal_brain/answer.py`
- Memory Router in `personal_brain/router.py`
- Router outputs:
  - `brain_index.json`
  - `memory/topics.json`
  - `memory/memory_manifest.json`
- secure vault in `personal_brain/vault.py`
- Feishu bridge MVP in `scripts/feishu_bridge.py`
- Feishu interaction audit in `interaction_logs`
- wxauto WeChat bridge shell in `scripts/wxauto_bridge.py`

Not implemented:

- weekly Markdown topics/insights review automation
- frontend
- knowledge graph visualization
- Neo4j
- GraphRAG
- multi-database deployment

## Commands

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
python brain.py build-router
```

Secure vault:

```powershell
python brain.py secure-add --label "..." --type password --username "..."
python brain.py secure-list
python brain.py secure-get "..."
```

Feishu bridge:

```powershell
python scripts/feishu_bridge.py --port 8787 --mode auto --ask-prefix "?"
```

## Architecture Rules

Non-negotiable:

- Preserve raw user input in `raw_messages`.
- Store AI-rewritten atomic memories in `memories`.
- Retrieval should use embeddings/RAG as the primary recall path.
- Topics, entities, type, importance, and confidence must be AI-generated.
- Broad memory category should guide navigation without replacing semantic recall.
- Answers must cite retrieved memory/raw-message evidence.
- Markdown/folders are exports or views, not the source of truth.
- Do not store secrets in normal memory.
- Do not send secrets to AI models.
- Do not build Neo4j, GraphRAG, visualization, or frontend unless explicitly revisited.

## Runtime Model Policy

Current intended setup:

- Chat/reasoning model: Z.AI `glm-5v-turbo`
- Chat endpoint: `https://api.z.ai/api/paas/v4`
- API key env var: `ZAI_API_KEY`
- Embedding model: Z.AI `embedding-3`
- Embedding dimension: `2048`

`personal_brain/llm.py` reads environment variables and, on Windows, falls back
to `HKCU\Environment` when a variable is not present in the current process.

Do not write real API keys, Feishu secrets, passwords, tokens, or local database
files into tracked project files.

## Current Memory Flow

Ingest:

```text
input text
-> raw_messages
-> AI structured extraction
-> memory_extraction_runs
-> memories
-> stable memory_category
-> topics/entities links
-> embed new memory IDs when embedding_model.enabled is true
-> rebuild Router
```

Current stable memory categories:

```text
现有项目改进
未来产品设想
生活感悟
产品使用技巧
自身认知更新
技术思考
人际关系
工作流方法
信息安全
临时待办
其他
```

Important boundary:

- `PersonalBrain.ingest(...)` owns post-ingest embeddings for newly created memory IDs.
- Adapters such as Feishu/WeChat should only receive/send messages and call the core brain.
- Feishu/WeChat must not duplicate memory extraction, embedding, database writes, recall, or answer logic.

Ask:

```text
question
-> semantic recall
-> AI rerank of candidate evidence
-> answer only from selected evidence
-> cite memory_id and raw_message_id
```

## Feishu Status

Feishu is the preferred MVP interaction channel because it uses an official bot
and event subscription rather than desktop UI automation.

Bridge facts:

- Event path: `/feishu/events`
- Health path: `/health`
- Supported event type: `im.message.receive_v1`
- Reply API: `POST /open-apis/im/v1/messages/{message_id}/reply`
- Token API: `POST /open-apis/auth/v3/tenant_access_token/internal`
- Modes: `remember`, `ask`, `auto`
- In `auto`, messages starting with `?` are answered; other text is remembered.
- MVP supports verification token, not encrypted event payloads.
- Bridge writes `interaction_logs` with user text, action, reply text, evidence,
  status, error, and latency for later quality review.

Required env vars:

```text
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_VERIFICATION_TOKEN
```

## WeChat Status

`scripts/wxauto_bridge.py` exists as a backup shell for Windows desktop WeChat.

Do not continue desktop WeChat UI automation unless the user explicitly resumes
it. Feishu is the preferred MVP channel for now.

## Secure Vault Boundary

Secrets must use `secure-add`, `secure-list`, and `secure-get`.

Secrets must not enter:

- `raw_messages`
- `memories`
- `memory_embeddings`
- Router manifests
- Markdown exports
- Git
- AI model calls

V0 uses Windows DPAPI plus master-password-derived entropy. Every decrypt
requires the master password.

## Documentation Roles

- `README.md`: current usage and setup
- `项目地图.md`: Chinese overview for the user
- `ARCHITECTURE.md`: architecture principles and review gates
- `.agents/project_memory.md`: this handoff memory for future Codex work

## Next Best Step

Do not jump to Neo4j, GraphRAG, frontend, or a new database.

Recommended next step:

```text
stabilize V0 smoke test
-> verify ingest/embed/recall/ask
-> verify Feishu remember/ask loop
-> then add weekly Markdown review automation
```

Weekly review should be Codex/AI reflective work:

```text
read Router + recent memories
-> synthesize Markdown topics
-> extract insights
-> preserve links back to evidence
```

User-captured future directions:

- Xiaochai should improve active judgment instead of passively storing text.
- It needs message withdrawal/correction that invalidates linked raw messages,
  memories, embeddings, Router entries, and logs consistently.
- MVP deletion/correction starts with ID-based memory archiving, not physical
  deletion: commands such as `删除 42` / `作废 42` mark the target memory as
  archived, remove its embedding from active recall, rebuild Router, keep raw
  evidence for audit/recovery, and should later evolve into reply-based
  deletion/correction.
- Replies and generated topics should default to Chinese.
- Memories should be less scattered: broad category first, dynamic topic second.
- Weekly Codex review should be a quality-control loop, not just a summary.
- Daily reports are first-version extraction snapshots plus deterministic issue
  markers, not an automatic worker. Use
  `python brain.py daily-report --date today` to generate a local
  `reports/YYYY-MM-DD.md` file containing same-day raw inputs, extraction runs,
  created/updated memories, interaction replies, errors, evidence JSON, and
  fixed-rule markers for pipeline issues such as extraction failure, explicit
  remember requests that produced no memory, Markdown noise in stored memories,
  interaction failures, and old reply citation formats. This command does not
  call AI, does not edit memories, and does not assume the runner has project
  memory loaded. Future Codex should read this project memory file before
  interpreting a report.
  `reports/` is git-ignored because it may contain private raw text.
- Daily report automation is intentionally narrow. `scripts/run_daily_report.ps1`
  only calls `python brain.py daily-report --last-hours 24`. The Codex App
  automation should run this at 12:00 every day, because the user's computer may
  be off at night. The backup Windows task installer
  `scripts/install_daily_report_task.ps1` also defaults to 12:00 and
  `LastHours=24`. Automation must not read reports, call Codex for analysis,
  call any AI model, diagnose, modify data, or repair anything.
- Later versions should add a memory lifecycle system like human memory:
  recent and frequently used memories stay sharp; old, low-value, or duplicate
  memories gradually lose recall weight, merge into higher-level summaries, or
  move to archived/superseded status while raw evidence remains preserved.
- Later versions should add image memory through a real media evidence layer:
  Feishu image/file events should preserve the original image or file reference,
  store metadata in a `media_assets`-style table, use a multimodal model for OCR
  and captioning, then feed the derived text into normal memory extraction only
  after checking whether the image is worth remembering and not obviously
  sensitive.
- Longer-term product direction includes relationship memory, decision-style
  memory, digital-twin behavior, and later external app integrations such as
  WeChat.
