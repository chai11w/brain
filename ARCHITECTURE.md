# AI-native Personal Brain Architecture

## Product North Star

Personal Brain is not a note-taking app, chat log archive, fixed folder tree,
keyword search tool, or CRUD database.

The product goal is:

```text
casual input
-> AI understands, rewrites, and structures it
-> long-term atomic memories are formed
-> semantic retrieval finds relevant evidence
-> AI reasons over retrieved evidence and answers
```

Code is infrastructure. The core product value is AI understanding, memory
formation, association, retrieval, and evidence-based reasoning.

## Non-Negotiable Principles

1. Raw user input is always preserved.
2. AI-rewritten atomic memories are the primary memory layer.
3. Retrieval should use embeddings/RAG as the primary recall path.
4. Topics, importance, entities, and memory type are identified dynamically by AI.
5. Answers must cite retrieved evidence and must not invent unsupported claims.
6. Fixed classification rules are temporary scaffolding only, never the product model.
7. Prompts and AI outputs are versioned so memory formation can be audited.
8. Secrets are not memories and must stay outside AI/model/Router flows.
9. Broad memory categories may guide review and navigation, but semantic recall
   remains the primary retrieval path.
10. Images and files need their own evidence layer. Do not treat OCR/caption
    text as the original raw message.

## Current V0 Shape

V0 is a local-first foundation:

```text
SQLite source of truth
-> AI memory extraction
-> embedding-backed recall
-> AI rerank
-> evidence-constrained answer
-> lightweight Router files for Codex/AI navigation
```

Implemented modules:

- `personal_brain/schema.py`: database foundation
- `personal_brain/extractor.py`: AI memory extraction
- `personal_brain/semantic.py`: embeddings and semantic recall
- `personal_brain/answer.py`: evidence-based answer generation
- `personal_brain/router.py`: Memory Router
- `personal_brain/memory_ops.py`: memory archive/lifecycle operations
- `personal_brain/daily_report.py`: local extraction/audit Markdown reports
- `personal_brain/vault.py`: encrypted secure vault
- `scripts/feishu_bridge.py`: Feishu interaction channel
- `scripts/wxauto_bridge.py`: WeChat shell

## Target Data Model

### raw_messages

Preserves exactly what the user sent. Never rewrite this table.

```sql
raw_messages (
  id INTEGER PRIMARY KEY,
  content TEXT NOT NULL,
  source TEXT NOT NULL,
  sender TEXT NOT NULL,
  created_at TEXT NOT NULL,
  metadata_json TEXT,
  processed_status TEXT NOT NULL
)
```

`processed_status` values:

- `pending`
- `processed`
- `ignored`
- `failed`

### memory_extraction_runs

Stores the AI processing trace for each raw message. This is required for
auditability.

```sql
memory_extraction_runs (
  id INTEGER PRIMARY KEY,
  raw_message_id INTEGER NOT NULL,
  model_provider TEXT NOT NULL,
  model_name TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  output_json TEXT NOT NULL,
  status TEXT NOT NULL,
  error TEXT,
  created_at TEXT NOT NULL
)
```

### memories

Stores AI-produced atomic memories. This is the primary memory layer.

```sql
memories (
  id INTEGER PRIMARY KEY,
  raw_message_id INTEGER NOT NULL,
  extraction_run_id INTEGER NOT NULL,
  content TEXT NOT NULL,
  title TEXT,
  memory_category TEXT NOT NULL,
  memory_type TEXT NOT NULL,
  importance REAL NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

Example raw input:

```text
I want Personal Brain to be AI-native, not a low keyword search tool.
```

Example atomic memory:

```text
User wants Personal Brain to rely on semantic understanding and reasoning rather
than keyword search.
```

`memory_category` is a broad navigation label such as:

```text
现有项目改进
未来产品设想
生活感悟
产品使用技巧
自身认知更新
学习
技术思考
人际关系
工作流方法
信息安全
临时待办
其他
```

This category is not a folder taxonomy. It is a stable review layer that helps
Codex and the user avoid scattered memories while keeping dynamic topics and
semantic retrieval as the real intelligence layer.

`学习` is the broad category for compact concept notes, definitions,
distinctions, analogies, and "I learned X means Y" records. It is not a
replacement for dynamic topics. Technical judgments remain `技术思考`, reusable
process patterns remain `工作流方法`, and direct Xiaochai/product changes remain
`现有项目改进`.

### memory_embeddings

Stores semantic vectors for each atomic memory.

```sql
memory_embeddings (
  memory_id INTEGER NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  vector_json TEXT NOT NULL,
  dimension INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (memory_id, provider, model)
)
```

For V0, vector JSON in SQLite is acceptable. When memory volume grows, migrate
to `sqlite-vec`, LanceDB, Qdrant, pgvector, or another vector index.

### topics

Topics are created and updated by AI. They are not hard-coded enums.

```sql
topics (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  parent_topic_id INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

### memory_topics

Associates memories with AI-discovered topics.

```sql
memory_topics (
  memory_id INTEGER NOT NULL,
  topic_id INTEGER NOT NULL,
  confidence REAL NOT NULL,
  reason TEXT,
  PRIMARY KEY (memory_id, topic_id)
)
```

### entities

Entities are extracted dynamically by AI.

```sql
entities (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL
)
```

### memory_entities

```sql
memory_entities (
  memory_id INTEGER NOT NULL,
  entity_id INTEGER NOT NULL,
  confidence REAL NOT NULL,
  PRIMARY KEY (memory_id, entity_id)
)
```

### secure_items

Secrets are stored separately from normal memory.

```sql
secure_items (
  id INTEGER PRIMARY KEY,
  label TEXT NOT NULL,
  secret_type TEXT NOT NULL,
  username TEXT,
  encrypted_value TEXT NOT NULL,
  encryption_scheme TEXT NOT NULL,
  kdf_name TEXT NOT NULL,
  kdf_salt TEXT NOT NULL,
  kdf_iterations INTEGER NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

### interaction_logs

Stores adapter-level interaction audit records, especially Feishu replies.
This enables later quality review of what the user sent, whether the system
remembered or answered, what it replied, what evidence was used, and what failed.

```sql
interaction_logs (
  id INTEGER PRIMARY KEY,
  message_id TEXT,
  source TEXT NOT NULL,
  sender TEXT NOT NULL,
  user_text TEXT NOT NULL,
  mode TEXT NOT NULL,
  action TEXT NOT NULL,
  raw_message_id INTEGER,
  reply_text TEXT,
  evidence_json TEXT,
  status TEXT NOT NULL,
  error TEXT,
  latency_ms INTEGER,
  created_at TEXT NOT NULL
)
```

### future media_assets

Image memory should preserve media evidence instead of flattening images into
plain text. A future media layer should store the source file reference,
local path or Feishu file key, checksum, media type, OCR text, caption,
model name, and link back to the triggering raw message.

```sql
media_assets (
  id INTEGER PRIMARY KEY,
  raw_message_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  media_type TEXT NOT NULL,
  file_path TEXT,
  external_file_key TEXT,
  sha256 TEXT,
  ocr_text TEXT,
  caption TEXT,
  model_name TEXT,
  created_at TEXT NOT NULL
)
```

Only the derived OCR/caption/summary should enter normal memory extraction, and
only after checking that the content is worth remembering and not obviously
sensitive.

## AI Memory Formation Pipeline

### Step 1: Ingest

Store the exact input in `raw_messages`.

The system must not lose or overwrite the original expression.

### Step 2: Understand And Rewrite

Call the configured chat model to produce structured JSON:

```json
{
  "should_remember": true,
  "reason": "The message describes a durable product principle.",
  "atomic_memories": [
    {
      "content": "User wants Personal Brain to be AI-native rather than keyword based.",
      "title": "AI-native memory principle",
      "memory_type": "principle",
      "importance": 0.94,
      "confidence": 0.91,
      "topics": [
        {
          "name": "AI-native Personal Brain",
          "reason": "The message defines the product direction."
        }
      ],
      "entities": [
        {
          "name": "Personal Brain",
          "type": "project"
        }
      ]
    }
  ]
}
```

Important rule:

```text
AI may polish, compress, and split the input.
AI must not change the user's meaning.
```

### Step 3: Persist AI Output

Store the raw AI JSON in `memory_extraction_runs`.

Store each extracted memory in `memories`.

Create or update AI-discovered topics and entities.

Assign each memory one broad `memory_category` for review/navigation.

### Step 4: Embed

Generate embeddings for each atomic memory when embedding is configured.

The embedding input should usually include:

```text
title
content
memory_type
memory_category
topics
entities
```

In V0, `PersonalBrain.ingest(...)` owns post-ingest embedding for newly created
memory IDs. Message adapters must not duplicate this logic.

### Step 5: Link Back To Evidence

Every memory must retain:

- `raw_message_id`
- `extraction_run_id`

This keeps the system explainable.

## RAG Query Pipeline

### Step 1: Query

The user's question is embedded as a semantic query.

Later versions may add AI query planning for filters and time ranges.

### Step 2: Semantic Recall

Retrieve nearest memories from `memory_embeddings`.

### Step 3: AI Rerank

Use AI to rerank candidates by relevance and evidence value.

Rerank output should include:

```json
{
  "memory_id": 123,
  "relevance": 0.96,
  "reason": "Directly states the user's architecture principle."
}
```

### Step 4: Evidence-Based Answer

Generate an answer only from selected memories and their linked raw messages.

Answer contract:

- Mention uncertainty when evidence is thin.
- Cite `memory_id` and `raw_message_id`.
- Do not infer beyond available evidence unless explicitly labeled as inference.
- If nothing relevant is found, say so.

## Memory Router

Router files are for lightweight AI navigation:

```text
brain_index.json
-> memory/topics.json
-> memory/memory_manifest.json
-> SQLite only for exact evidence
```

The Router is not the vector store and not RAG. It helps Codex and other AI
callers avoid reading the full database every time.

## Markdown Is An Export Layer

Markdown files are for human reading and Codex review.

They are not the source of truth.

Source of truth:

```text
raw_messages
memories
memory_embeddings
topics
entities
memory_extraction_runs
secure_items for encrypted secrets
```

Current daily Markdown reports are extraction/audit snapshots generated from the
database. They may include deterministic issue markers, but they must not become
the source of truth and the automation must not modify data.

Weekly Memory Compression review is a near-term reflective layer. It should be
generated from the database and Router through AI synthesis, with evidence links
preserved. Its purpose is not merely to display a Markdown digest, but to
compress short-term or scattered memories into candidate durable long-term
memories for review before anything is written back.

## Codex Role

Codex should be used for reflective and architectural work:

- weekly synthesis
- topic consolidation
- insight extraction
- contradiction detection
- memory quality review
- prompt improvement
- migration planning
- architecture review

Codex should not replace the real-time memory ingestion path.

Real-time path:

```text
Feishu / WeChat / CLI
-> PersonalBrain.ingest(...)
-> AI extraction
-> database
-> embeddings when configured
-> Router update
-> lightweight reply
```

## Explicitly Out Of Scope For V0

- frontend
- knowledge graph UI
- Neo4j
- GraphRAG
- multi-database deployment
- image/file memory ingestion
- complex agent orchestration
- fixed taxonomy
- keyword search as the main retrieval path

## Architecture Gate For Future Changes

Before accepting any feature, ask:

1. Does this preserve raw input?
2. Does this improve AI memory formation or evidence-based recall?
3. Does this rely on semantic retrieval rather than only text matching?
4. Does this keep answers evidence-based?
5. Does this avoid hard-coded product intelligence?
6. Does this keep secrets out of normal AI memory?
7. Does this make the system more like a second brain, not more like a CRUD app?

If the answer is no, reject or redesign the feature.
