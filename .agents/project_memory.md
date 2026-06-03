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
