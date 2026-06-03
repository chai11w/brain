# Personal Brain V0 Foundation

This repo is building an AI-native Personal Brain.

Current stage:

```text
database foundation
-> memory router
```

Not current stage:

```text
message ingestion
AI extraction
embedding/RAG retrieval
WeChat adapter
knowledge graph
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

## Stats

```powershell
python brain.py stats
```

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
- No message ingestion pipeline yet.
- No model calls yet.

The next correct step is AI memory extraction:

```text
raw message
-> AI rewrite/split
-> atomic memories
-> dynamic topics/entities/importance
-> embeddings
-> router update
```
