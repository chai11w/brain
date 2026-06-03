# AI-native Personal Brain Architecture

## Product North Star

Personal Brain is not a note-taking app, a chat log archive, or a keyword search tool.

The product goal is:

```text
casual input
-> AI understands, rewrites, and structures it
-> long-term atomic memories are formed
-> semantic retrieval finds relevant evidence
-> AI reasons over retrieved evidence and answers
```

Code is infrastructure. The core product value is AI understanding, memory formation,
association, retrieval, and evidence-based reasoning.

## Non-Negotiable Principles

1. Raw user input is always preserved.
2. AI-rewritten atomic memories are the primary memory layer.
3. Retrieval must use embeddings and RAG, not only keyword matching.
4. Topics, importance, entities, and memory type are identified dynamically by AI.
5. Answers must cite retrieved evidence and must not invent unsupported claims.
6. Fixed classification rules are temporary scaffolding only, never the product model.
7. Prompts and AI outputs are versioned so memory formation can be audited.

## Review Of Current Implementation

The current implementation is useful only as a runnable demo shell. It should not be
treated as the final foundation.

### What Is Acceptable Temporarily

- A command-line entry point exists.
- A thin `handle_message(text, sender, source)` interface exists for future WeChat adapters.
- SQLite is acceptable as the first local durable store.
- Markdown output is acceptable as a human-readable export layer.
- The OpenAI-compatible LLM config direction is acceptable.

### What Does Not Meet The Product Goal

- `memories` currently stores raw text directly. This collapses the raw input layer and
  the AI memory layer into one table.
- `search()` currently uses `LIKE` and `difflib`. This is keyword/fuzzy search, not RAG.
- `weekly.py` uses fixed topic rules. This is not AI-native classification.
- LLM is currently optional decoration instead of the center of memory formation.
- There is no embedding pipeline, vector index, reranking, or evidence graph.
- There is no prompt versioning or AI processing audit trail.
- Query answers do not have a strict evidence contract.

Conclusion:

```text
Current code can stay as a disposable prototype.
The real foundation must be rebuilt around raw_messages, atomic memories, embeddings,
AI topics, and evidence-based answers.
```

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

Stores the AI processing trace for each raw message. This is required for auditability.

```sql
memory_extraction_runs (
  id INTEGER PRIMARY KEY,
  raw_message_id INTEGER NOT NULL,
  model_provider TEXT NOT NULL,
  model_name TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  output_json TEXT NOT NULL,
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
我觉得别搞那种 low 的关键词搜索，我要的是 AI 会理解和推导的第二大脑。
```

Example atomic memory:

```text
User wants Personal Brain to be AI-native: memory retrieval should rely on semantic
understanding and reasoning rather than keyword search.
```

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

For V0.1, vector JSON in SQLite is acceptable. When memory volume grows, migrate to
`sqlite-vec`, LanceDB, Qdrant, pgvector, or another vector index.

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
      "content": "User wants Personal Brain to be AI-native rather than a keyword-based note tool.",
      "title": "AI-native memory principle",
      "memory_type": "product_principle",
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
          "type": "product"
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

### Step 4: Embed

Generate embeddings for each atomic memory.

The embedding input should usually include:

```text
title
content
memory_type
topics
entities
```

### Step 5: Link Back To Evidence

Every memory must retain:

- `raw_message_id`
- `extraction_run_id`

This keeps the system explainable.

## RAG Query Pipeline

### Step 1: Query Understanding

Use AI to rewrite the user question into a retrieval plan:

```json
{
  "intent": "recall_prior_thinking",
  "semantic_query": "user's prior thinking about AI-native Personal Brain architecture",
  "filters": {
    "topics": ["AI-native Personal Brain"],
    "time_range": null,
    "memory_types": ["product_principle", "architecture_decision"]
  }
}
```

### Step 2: Semantic Recall

Embed `semantic_query`.

Retrieve nearest memories from the vector index.

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
- Cite memory IDs or dates.
- Do not infer beyond available evidence unless explicitly labeled as inference.
- If nothing relevant is found, say so.

## Model Abstraction

The system should support interchangeable providers:

- OpenAI
- DeepSeek
- Tongyi/Qwen
- Kimi
- Zhipu
- OpenRouter
- Ollama/vLLM with OpenAI-compatible endpoints

Required capabilities:

```text
chat completion
embedding
structured JSON output or JSON-repair fallback
```

Config shape:

```json
{
  "chat": {
    "provider": "openai_compatible",
    "base_url": "https://api.example.com/v1",
    "api_key_env": "BRAIN_CHAT_API_KEY",
    "model": "chat-model-name"
  },
  "embedding": {
    "provider": "openai_compatible",
    "base_url": "https://api.example.com/v1",
    "api_key_env": "BRAIN_EMBEDDING_API_KEY",
    "model": "embedding-model-name",
    "dimension": 1536
  }
}
```

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
AI processing runs
```

Markdown should be generated from the database through AI summarization.

## Codex Skill Role

Codex skills are best used for slower reflective work:

- weekly synthesis
- topic consolidation
- insight extraction
- contradiction detection
- memory quality review
- prompt improvement
- migration planning

They should not replace the real-time memory ingestion service.

The real-time path must still be:

```text
WeChat adapter
-> message handler
-> AI extraction
-> database
-> lightweight reply
```

## V0.1 Scope

The next implementation should replace the current low-fidelity prototype with:

1. `raw_messages` table.
2. `memories` table for AI atomic memories.
3. `memory_extraction_runs` audit table.
4. OpenAI-compatible chat client with strict JSON output.
5. OpenAI-compatible embedding client.
6. SQLite vector storage as JSON for the first pass.
7. Semantic retrieval plus AI rerank.
8. Evidence-based answer generation.
9. Dynamic AI topics.

Explicitly out of scope for V0.1:

- frontend
- knowledge graph UI
- Neo4j
- multi-database deployment
- complex agent orchestration
- fixed taxonomy

## Architecture Gate For Future Changes

Before accepting any feature, ask:

1. Does this preserve raw input?
2. Does this improve AI memory formation?
3. Does this rely on semantic retrieval rather than only text matching?
4. Does this keep answers evidence-based?
5. Does this avoid hard-coded product intelligence?
6. Does this make the system more like a second brain, not more like a CRUD app?

If the answer is no, reject or redesign the feature.

