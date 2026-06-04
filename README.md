# Personal Brain V0 Foundation

This repo is building an AI-native Personal Brain.

Current stage:

```text
database foundation
-> memory router
-> AI memory extraction
-> embedding-backed semantic recall
-> evidence-constrained ask
-> Feishu / WeChat bridge shells
```

Not current stage:

```text
knowledge graph
GraphRAG / Neo4j
frontend
weekly Markdown review automation
```

## Architecture Position

The source of truth is SQLite. Folders and Markdown are only future export
views, not the core memory structure.

The foundation is:

- `raw_messages`: exact original user input
- `memory_extraction_runs`: AI processing audit trail
- `memories`: AI-rewritten atomic memories
- `memory_embeddings`: vectors for semantic retrieval
- `topics`: AI-discovered dynamic topics
- `memory_topics`: many-to-many memory/topic links
- `entities`: AI-discovered entities
- `memory_entities`: many-to-many memory/entity links

This prevents the project from turning into a folder tree, keyword note app, or
fixed-category CRUD system.

## Initialize The Foundation

```powershell
python brain.py init-db
```

If an old prototype `memories` table exists, it is renamed to `legacy_memories`.
Those rows remain available as evidence, but they are not treated as AI atomic
memories.

## Build The Memory Router

```powershell
python brain.py build-router
```

This generates:

- `brain_index.json`
- `memory/topics.json`
- `memory/memory_manifest.json`

AI callers should read in this order:

```text
brain_index.json
-> memory/topics.json
-> memory/memory_manifest.json
-> SQLite only for exact evidence
```

The router is a navigation layer. It is not RAG and does not perform semantic
retrieval.

## Ingest A Memory

After configuring the chat model, ingest one raw thought:

```powershell
python brain.py ingest "我希望 Personal Brain 是 AI-native 的，而不是普通关键词搜索。"
```

This command:

1. stores the exact input in `raw_messages`
2. asks the chat model to extract structured atomic memories
3. records the model output in `memory_extraction_runs`
4. stores AI-rewritten memories in `memories`
5. creates dynamic `topics` and `entities`
6. rebuilds the Memory Router

If `embedding_model.enabled` is true, newly extracted memories are embedded by
the core ingest flow so every message entry behaves consistently across CLI,
Feishu, and WeChat.

Review extracted memories:

```powershell
python brain.py memory-list
python brain.py memory-show 1
```

Use these before building embeddings. They let you check whether the AI
understood the original input, split it correctly, and avoided changing meaning.

## Build Embeddings And Recall

After memory quality looks acceptable, configure `embedding_model` in
`config.json`, then generate missing embeddings:

```powershell
python brain.py embed-memories
```

Semantic recall uses the stored vectors in SQLite and returns candidate memories
with raw evidence:

```powershell
python brain.py recall "AI-native Personal Brain architecture"
```

This is the first retrieval layer. It finds candidate memories by semantic
similarity and returns raw evidence for review.

## Ask From Evidence

After embeddings exist, `ask` retrieves candidate memories, asks the chat model
to rerank the evidence, and answers only from selected memory/raw-message
evidence:

```powershell
python brain.py ask "What did I previously decide about Personal Brain architecture?"
```

The answer should cite `memory_id` and `raw_message_id`. If evidence is thin, it
should say so instead of inventing an answer.

## Message Adapter Entry

`PersonalBrain.handle_message(text, sender, source)` is the unified entry for
future WeChat adapters.

Current behavior:

```text
text message
-> ingest
-> raw_messages / memories / topics / entities
-> rebuild router
-> reply "已记住。"
```

For a local HTTP bridge:

```powershell
python scripts/webhook_server.py --port 8765
```

POST JSON to `/message`:

```json
{
  "text": "我今天想到一个新产品原则。",
  "sender": "me",
  "source": "wechat"
}
```

This is not the final WeChat client integration yet. It is the stable adapter
boundary that wxauto, Wechaty, or another bridge can call.

## Wxauto WeChat Bridge

For the Windows desktop WeChat client, this repo has a minimal `wxauto4` shell.
The intended final shape is a separate WeChat account/persona such as Xiaochai.
Before that exists, use a dedicated chat or group such as `?????`.
Do not use File Transfer Assistant as the long-running memory inbox, because it
will pollute normal file/image transfer workflows.

```powershell
python scripts/wxauto_bridge.py --chat "?????" --mode remember
```

Modes:

- `remember`: every received text message is passed to
  `PersonalBrain.handle_message(...)` and stored as memory.
- `ask`: every received text message is answered through `brain.ask(...)`.
- `auto`: messages starting with `?` are answered, other messages are stored.

Example:

```powershell
python scripts/wxauto_bridge.py --chat "?????" --mode auto --ask-prefix "?"
```

If you do not have a second WeChat account yet, run the bridge from your current
account and add `--include-self` so messages you send into the dedicated
Xiaochai inbox can be processed too:

```powershell
python scripts/wxauto_bridge.py --chat "?????" --mode auto --ask-prefix "?" --include-self
```

The bridge only receives and sends WeChat text. It does not own model calls,
database writes, memory extraction, retrieval, or answering logic.

## Feishu Memory Inbox

Feishu is the preferred MVP interaction channel. It uses an official Feishu app
bot and event subscription, not desktop automation.

Flow:

```text
Feishu message
-> scripts/feishu_bridge.py
-> PersonalBrain.handle_message(...) or PersonalBrain.ask(...)
-> reply to Feishu
```

Run locally:

```powershell
python scripts/feishu_bridge.py --port 8787 --mode auto --ask-prefix "?"
```

Modes:

- `remember`: store every text message as memory.
- `ask`: answer every text message from memory evidence.
- `auto`: messages starting with `?` are answered; other messages are stored.

Required environment variables:

```powershell
setx FEISHU_APP_ID "your app id"
setx FEISHU_APP_SECRET "your app secret"
setx FEISHU_VERIFICATION_TOKEN "your event verification token"
```

Restart the terminal after `setx`, or start the bridge from a shell that already
has these variables.

Feishu app setup:

1. Create a custom app in Feishu Open Platform.
2. Enable Bot capability.
3. Add the bot to the target chat or group.
4. Add permissions for receiving messages and replying/sending messages.
5. In Event Subscription, subscribe to `im.message.receive_v1`.
6. Configure Request URL:

```text
https://your-public-domain/feishu/events
```

7. Leave Encrypt Key empty for MVP. The bridge supports verification token, but
   encrypted events are deliberately out of scope for the first pass.
8. Use a tunnel such as ngrok or cloudflared for local debugging:

```powershell
cloudflared tunnel --url http://127.0.0.1:8787
```

Health check:

```text
http://127.0.0.1:8787/health
```

## Stats

```powershell
python brain.py stats
```

## Secure Vault

Sensitive secrets are not normal memories. Passwords, API keys, tokens, and
private notes must not go through AI extraction, Router manifests, embeddings,
or Markdown exports.

This project has a separate local encrypted vault:

```powershell
python brain.py secure-add --label "GitHub main" --type password --username chai11w
python brain.py secure-list
python brain.py secure-get "GitHub main"
```

`secure-add` and `secure-get` ask for a master password every time. V0 uses
Windows DPAPI plus master-password-derived entropy. The database stores only
encrypted values.

Important boundaries:

- secrets are not sent to the chat model
- secrets are not written to `memories`
- secrets are not included in `brain_index.json`
- secrets are not included in `memory/memory_manifest.json`
- secrets are not committed to Git

## Configure Chat Model

The first real AI layer will use a chat model to rewrite casual input into
atomic memories.

For Z.AI GLM-5V-Turbo, create `config.json` from `config.example.json`, then set
the API key in your current PowerShell session:

```powershell
$env:ZAI_API_KEY="your real key"
```

Do not put real API keys in project files.

Test the model connection:

```powershell
python brain.py test-chat "请用一句话回复：模型已接通。"
```

This only verifies the model channel. It does not ingest memory yet.

## What This Version Deliberately Does Not Do

- No fixed topic folders.
- No hard-coded classification.
- No keyword/fuzzy search.
- No GraphRAG, Neo4j, or visualization.
- No knowledge graph, GraphRAG, Neo4j, or visualization.
- No frontend.
- No fixed topic folders.
- No hard-coded classification.
- No keyword/fuzzy search as the primary recall path.
- No weekly Markdown review automation yet.

The next correct step is AI memory extraction:

```text
Feishu / WeChat / CLI message
-> raw_messages
-> AI rewrite/split
-> atomic memories
-> dynamic topics/entities/importance
-> embeddings when configured
-> router update
-> recall/ask from evidence
```
