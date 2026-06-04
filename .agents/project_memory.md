# Project Memory: AI-native Personal Brain

This is project-scoped memory for Codex/AI agents working in this repository.
Do not treat it as global memory.

## User Goal

The user is building an AI-native Personal Brain, not a simple note app, CRUD
tool, keyword search system, or fixed folder taxonomy.

The product goal:

```text
casual input
-> AI understands, rewrites, and structures it
-> long-term atomic memories are formed
-> semantic retrieval finds relevant evidence
-> AI reasons over retrieved evidence and answers
```

The user wants Codex to act as a technical partner and architecture reviewer,
not merely an executor.

## Required Working Style

Before implementing a request, evaluate it through the product goal:

1. Does it fit AI-native Personal Brain?
2. Is it too low-level, too CRUD-like, or too keyword/folder based?
3. What is the better architecture?
4. Should code be changed now, or should the design be clarified first?

Push back when needed.

## User Communication Preference

The user is not deeply technical and prefers Chinese explanations with more
context for professional concepts.

When explaining architecture, database schema, router, RAG, embeddings, or AI
pipelines:

- explain in plain Chinese first
- say why the piece exists
- say how it connects to other pieces
- then mention the related file/code

Avoid overly terse technical summaries.

## Current Project State

Completed:

- `ARCHITECTURE.md`: architecture principles
- `项目地图.md`: Chinese project map for the user
- AI-native database foundation in `personal_brain/schema.py`
- Memory Router in `personal_brain/router.py`
- router outputs:
  - `brain_index.json`
  - `memory/topics.json`
  - `memory/memory_manifest.json`

Current database:

- `data/personal_brain.sqlite3`
- formal AI-native tables exist:
  - `raw_messages`
  - `memory_extraction_runs`
  - `memories`
  - `memory_embeddings`
  - `topics`
  - `memory_topics`
  - `entities`
  - `memory_entities`
- old prototype rows were migrated to `legacy_memories`

Important: `legacy_memories` is evidence only. It is not AI-extracted atomic
memory.

## Current Commands

```powershell
python brain.py init-db
python brain.py build-router
python brain.py stats
```

Do not reintroduce old `ask`, keyword search, fixed weekly classification, or
raw-message-to-memories storage as the main product path.

## File Roles

- `项目地图.md`: user-facing Chinese overview
- `ARCHITECTURE.md`: architecture constitution
- `README.md`: current stage usage
- `brain.py`: CLI entrypoint
- `personal_brain/schema.py`: database foundation
- `personal_brain/router.py`: router index builder
- `brain_index.json`: AI/Codex entrypoint for memory routing
- `memory/topics.json`: lightweight topic routing table
- `memory/memory_manifest.json`: lightweight memory manifest
- `data/personal_brain.sqlite3`: source-of-truth database

## Architecture Rules

Non-negotiable:

- Preserve raw user input in `raw_messages`.
- Store AI-rewritten atomic memories in `memories`.
- Retrieval must become embedding/RAG based, not only keyword matching.
- Topics, entities, type, importance, and confidence must be AI-generated.
- Answers must cite retrieved evidence and avoid unsupported claims.
- Markdown/folders are exports or views, not the source of truth.
- Do not build Neo4j, GraphRAG, or visualization unless explicitly revisited.

## Next Correct Step

The next foundation step is AI memory extraction:

```text
incoming text
-> raw_messages
-> chat model extracts structured JSON
-> memory_extraction_runs records the AI output
-> memories stores atomic memories
-> topics/entities links are created
-> embeddings are generated later
-> router is rebuilt
```

Do not jump to WeChat, frontend, weekly automation, or retrieval before the AI
memory extraction foundation is designed and implemented.

## Update: AI Memory Extraction V1

`personal_brain/extractor.py` now implements first-pass AI memory extraction.

Available command:

```powershell
python brain.py ingest "..."
```

It stores raw input in `raw_messages`, asks the configured chat model for
structured JSON, records the run in `memory_extraction_runs`, writes atomic
memories to `memories`, links dynamic topics/entities, and rebuilds the Memory
Router.

This is not retrieval yet. It does not create embeddings and does not answer
questions.

Memory quality review commands:

```powershell
python brain.py memory-list
python brain.py memory-show 1
```

Use these to inspect AI memory content, raw evidence, topics, entities,
importance, confidence, model, and prompt version before building embeddings.

Next correct foundation step:

```text
memories
-> embedding model
-> memory_embeddings
-> semantic recall foundation
```

## Update: Secure Vault V1

The project now has a separate secure vault for sensitive items.

Commands:

```powershell
python brain.py secure-add --label "..." --type password --username "..."
python brain.py secure-list
python brain.py secure-get "..."
```

Security boundary:

- secrets must not be sent to AI models
- secrets must not be stored in `raw_messages` or `memories`
- secrets must not appear in Router files
- secrets must not be embedded
- secrets must not be committed to Git

V0 uses Windows DPAPI plus master-password-derived entropy. Every decrypt
requires the master password. This is a local vault, not an AI memory flow.

## Update: Message Adapter Boundary

`PersonalBrain.handle_message(text, sender, source)` is now the stable entry for
future WeChat adapters.

Behavior:

```text
text message
-> ingest
-> AI memory extraction
-> router rebuild
-> lightweight reply
```

`scripts/webhook_server.py` exposes this as a local HTTP bridge. Real wxauto,
Wechaty, or other WeChat integrations should call this boundary instead of
duplicating memory logic.

## Update: Wxauto Bridge V1

`scripts/wxauto_bridge.py` is the first desktop WeChat shell.

It uses the official/free `wxauto4` package and follows the wxauto listener
shape:

```text
WeChat()
-> AddListenChat(chat_name, callback)
-> KeepRunning()
```

Commands:

```powershell
python scripts/wxauto_bridge.py --chat "你的主号昵称" --mode remember
python scripts/wxauto_bridge.py --chat "你的主号昵称" --mode auto --ask-prefix "?"
```

Modes:

- `remember`: store every incoming text through `PersonalBrain.handle_message`.
- `ask`: answer every incoming text through `brain.ask`.
- `auto`: messages with the ask prefix are answered; other text is remembered.

Boundary:

- The bridge owns only WeChat receive/send.
- It must not duplicate memory extraction, database writes, model calls,
  semantic recall, or answer generation logic.
- Core logic stays in `PersonalBrain`.

Runtime notes:

- `wxauto4` was installed in the local Python environment.
- `wxauto4/comtypes` needs a generated COM cache; the bridge redirects that to
  `.tmp_comtypes_cache/` inside the workspace so Codex sandbox runs do not try
  to write `%APPDATA%`.
- The bridge has been import-tested, but full runtime requires desktop WeChat
  to be open and logged in.
- The final product shape is a separate WeChat account/persona such as `小柴`.
  If the user has no second WeChat account yet, use the current account as a
  temporary memory inbox with `--include-self`. This is not the final
  human-like Xiaochai experience, but it is enough to collect memory and test
  recall/ask behavior.

### Wxauto Bridge Usage Correction

Do not use File Transfer Assistant as a long-running Personal Brain inbox. The
user uses it for normal file/image transfer, and Personal Brain replies would
make it noisy.

Use a dedicated chat or group instead, for example:

```powershell
python scripts/wxauto_bridge.py --chat "小柴记忆箱" --mode remember
python scripts/wxauto_bridge.py --chat "小柴记忆箱" --mode auto --ask-prefix "?"
python scripts/wxauto_bridge.py --chat "小柴记忆箱" --mode auto --ask-prefix "?" --include-self
```

If there is no second WeChat account yet, use the current account as a temporary
inbox with `--include-self` inside that dedicated chat/group. The final product
shape remains a separate WeChat account/persona such as Xiaochai.

## Update: Feishu Bridge MVP

The user paused wxauto/wxauto4 debugging. Keep `scripts/wxauto_bridge.py` as a
backup, but do not continue debugging desktop WeChat UI automation for now.

Feishu is now the preferred MVP interaction channel because it is the user's
main work platform and does not depend on desktop window recognition.

Target flow:

```text
Feishu message
-> scripts/feishu_bridge.py
-> PersonalBrain.handle_message(...) or PersonalBrain.ask(...)
-> reply to Feishu
```

Implementation:

- `scripts/feishu_bridge.py` exposes an HTTP server.
- Event URL path: `/feishu/events`
- Health path: `/health`
- Event type: `im.message.receive_v1`
- Reply API: `POST /open-apis/im/v1/messages/{message_id}/reply`
- Tenant token API:
  `POST /open-apis/auth/v3/tenant_access_token/internal`
- Modes match wxauto bridge:
  - `remember`
  - `ask`
  - `auto`
- In `auto`, messages starting with `?` are answered; other text is remembered.

Environment variables:

```powershell
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_VERIFICATION_TOKEN
```

Security boundary:

- Do not write Feishu app secret into tracked project files.
- App secret should live in user-level environment variables or a local secret
  manager.
- MVP supports verification token but not encrypted events. Leave Encrypt Key
  empty in Feishu Event Subscription for now.

Deployment setup:

1. Create custom Feishu app.
2. Enable Bot capability.
3. Add bot to the target chat/group.
4. Grant receive-message and send/reply-message permissions.
5. Subscribe to `im.message.receive_v1`.
6. Configure Event Subscription Request URL to a public tunnel:
   `https://.../feishu/events`.
7. Run local bridge:

```powershell
python scripts/feishu_bridge.py --port 8787 --mode auto --ask-prefix "?"
```

Local logic tests passed with fake Feishu payloads. Real callback test still
requires setting the Feishu environment variables and public tunnel URL.

## Update: Semantic Recall V1

The project now has a first-pass embedding and semantic recall foundation.

Available commands:

```powershell
python brain.py embed-memories
python brain.py recall "..."
```

Implementation:

- `personal_brain/llm.py` includes `EmbeddingClient` for OpenAI-compatible
  `/embeddings` APIs.
- `personal_brain/config.py` supports `embedding_model` config.
- `personal_brain/semantic.py` writes vectors to `memory_embeddings` and uses
  cosine similarity for recall.
- Recall returns candidate memories with raw evidence, but it is not yet the
  final evidence-based answer generator.

Next foundation step after this layer:

```text
semantic recall candidates
-> AI rerank
-> evidence-constrained answer
-> citations to memory/raw evidence
```

## Update: Evidence Answer V1

The project now has a first-pass evidence-based answer layer.

Available command:

```powershell
python brain.py ask "..."
```

Implementation:

- `personal_brain/answer.py` defines `AnswerEngine`.
- `ask` performs semantic recall first.
- The chat model reranks recalled memories as evidence.
- The final answer prompt requires answering only from provided evidence and
  citing `memory_id` / `raw_message_id`.

Important boundary:

- This is the new AI-native `ask`, not the old keyword-search answer path.
- It requires both embeddings and chat model configuration.
- If evidence is missing or weak, the answer should say so rather than invent.

## Update: Model Runtime Configuration

The user's `ZAI_API_KEY` is stored in the Windows user-level environment
variables. Codex-launched processes may not inherit that variable automatically,
so `personal_brain/llm.py` now falls back to reading `HKCU\Environment` on
Windows when `os.environ` does not contain the requested key.

Model policy:

- The fixed primary model is `glm-5v-turbo`.
- Use `glm-5v-turbo` for memory extraction, structured JSON, rerank, evidence
  answering, planning, and any natural-language reasoning/generation.
- Do not casually switch the primary chat/reasoning model to another model.
- `embedding-3` may be used only as a technical embedding/vectorization
  component because embeddings are a separate API capability from chat
  completion. It is not the product's reasoning model.
- If the user requires literally only `glm-5v-turbo` and no embedding model at
  all, then semantic vector retrieval must be disabled or redesigned as
  GLM-based reranking over router/manifest candidates; that is slower and less
  scalable and should not be described as embedding/RAG.

Current working runtime setup:

- Chat: Z.AI OpenAI-compatible endpoint `https://api.z.ai/api/paas/v4`
- Fixed primary chat/reasoning model: `glm-5v-turbo`
- Embedding: Z.AI OpenAI-compatible endpoint `https://api.z.ai/api/paas/v4`
- Embedding model: `embedding-3`
- Embedding dimension: `2048`

Real closed-loop test passed:

```powershell
python -B brain.py test-chat "请用一句话回复：模型已接通。"
python -B brain.py embed-memories
python -B brain.py recall "Personal Brain 回答问题的原则" --limit 3
python -B brain.py ask "我之前对 Personal Brain 回答问题有什么要求？"
```

Observed result:

- `embed-memories` wrote 2 embeddings.
- `recall` returned memory #2 and #1 with raw evidence.
- `ask` answered in Chinese and cited `[memory_id=..., raw_message_id=...]`.
- CLI stdio is configured as UTF-8 in `brain.py` to avoid Chinese mojibake in
  Codex/PowerShell output.

## Handoff Before Next Chat

Current stable state:

- Unified message entry is done: `PersonalBrain.handle_message(text, sender, source)` now calls `ingest`.
- Local HTTP bridge exists: `scripts/webhook_server.py` exposes `POST /message`.
- WeChat adapter example exists: `scripts/wechat_adapter_example.py`.
- Wxauto bridge exists: `scripts/wxauto_bridge.py`.
- Wxauto/wxauto4 debugging is paused. Keep the bridge as backup, but do not
  continue desktop WeChat UIAutomation unless the user explicitly resumes it.
- Semantic recall V1 exists: `embed-memories` stores vectors and `recall` returns evidence-bearing candidates.
- Evidence Answer V1 exists: `ask` does recall, AI rerank, and evidence-constrained answering.
- Real model closed-loop has passed with fixed primary model `glm-5v-turbo`
  plus Z.AI `embedding-3` as the embedding-only component.
- Feishu bridge exists: `scripts/feishu_bridge.py`.
- Feishu is now the primary MVP interaction channel.
- Feishu bridge has been deployed locally through a temporary cloudflared tunnel
  and has successfully received/replied to real Feishu messages.
- Feishu Event Subscription URL used in this session:
  `https://enhance-ssl-weeks-medical.trycloudflare.com/feishu/events`
  This is a temporary quick tunnel URL and may change after restart.
- Feishu app credentials were provided by the user during the session. Do not
  write secrets into tracked files. Prefer runtime/user-level environment
  variables.
- Current Feishu bridge mode: `auto`, ask prefix supports both `?` and Chinese
  full-width `？`.
- The bridge adds an `OK` reaction when a message is accepted so the user can
  tell it has started working.
- Successful memory writes currently auto-run `embed_missing_memories`, so new
  memories can be queried sooner.
- A transient TLS EOF occurred while calling Feishu reply API; retry logic was
  added to `request_json`.
- Future WeChat shell must only handle message receive/send and call `handle_message`; it must not duplicate memory extraction logic.
- Important UX decision for next chat: after a memory is written, Feishu should
  reply with a compact list of the actual memory contents, not only
  "小柴记住了", and not a noisy "topic + content + metadata" card. Best proposed
  format:

```text
小柴记住了 2 条：

1. 用户希望飞书作为 Personal Brain 的主要记忆收集入口。
2. 用户认为普通消息用于记忆，? 开头用于查询。
```

- If the model decides not to remember, reply naturally:

```text
小柴收到了，但这句更像临时对话，我先不存。
```

- The user explicitly reminded Codex not to mechanically follow instructions.
  Before changing behavior, judge the goal, risk, and better architecture.
- Local latest commit: `e93e44a Wire message adapter to ingestion`.
- GitHub repo: `chai11w/brain`.
- Remote latest commit observed: `24f03c321e7cf2a9787ba9eb24a7ee3565b032e3`.
