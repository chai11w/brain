# Xiaochai Backlog Review

Project-scoped backlog and decision table for Xiaochai / AI-native Personal Brain.
Do not ingest this file into Xiaochai's personal memory database.

Purpose:

- Separate active fixes from product direction and background ideas.
- Avoid treating every Xiaochai-related memory as immediate engineering work.
- Give future Codex sessions a maintained view of what to change now, what is already done, what is intentionally deferred, and what should only update docs.

Maintenance rule:

- Update this file after reviewing Xiaochai-related memories or daily reports.
- Move items between sections when implementation or product judgment changes.
- Remove or compress items that are no longer useful after several stable review cycles.

## Recently Worth Changing

These are close to the current V0 foundation and can become code or prompt work after a small design check.

### Same-Day Todo Recall

- Related memories: `94`, `95`, `100`, `101`, `107`, `120`, `127`
- Current reading: Xiaochai should not become a full reminder system right now. The user's immediate need is simpler: when the user asks on the day itself, such as `?今天要做什么`, Xiaochai should be able to recognize and return relevant same-day or currently active temporary todos from stored memories.
- Current status: initial recall/answer tuning is implemented. `今天要做什么` now ranks `临时待办` memories first in local recall and answers with concrete todos before product-feature discussion.
- Recommended next step: verify through Feishu in real use. If it returns stale or already-completed temporary todos, add lightweight completion/expiry handling later.
- Likely change type: retrieval/answer tuning, not scheduled reminder automation.

### Recall Quality, Router, Evidence, And Summary

- Related memories: `40`, `75`, `77`, `81`, `84`, `85`, `96`, `97`, `138`
- Current reading: these are the real middle-layer improvements after basic extraction stabilizes: better recall, read-time dedupe, routing, evidence answers, and periodic summary.
- Recommended next step: keep using the current system until recall failures appear in real questions, then fix the smallest failing layer.
- Likely change type: code over several small passes.

### Weekly Memory Compression Review

- Related memories: `145`, `153`, `154`, `155`
- Current reading: the user has clarified that weekly/monthly reports are not mainly for display. Their value is compressing short-term memories that may otherwise decay or disappear into durable long-term memories, while also showing what each broad category contains.
- First review window: start at `2026-06-04 00:00:00` because June 4 has about 50 stored memories and captures Xiaochai's dense first-week formation period. End at the latest available memory/report time for the first run.
- First version execution:
  1. Read memories, raw messages, topics, and interactions from the selected window.
  2. Group memories by `memory_category`.
  3. For each category, list the main themes, repeated ideas, and evidence IDs.
  4. Identify durable value inside short-term or stage-specific memories: reusable principles, workflows, preferences, concepts, or mechanism judgments.
  5. Identify temporary-memory candidates that are expired, likely expired, or still active.
  6. Output durable-value extraction candidates and upper-level summary candidates with evidence IDs, but do not write them into the database.
  7. Output archive/observe suggestions for temporary memories, but do not archive automatically.
- Output target: a local review Markdown file such as `reports/weekly-compression-2026-06-04-to-2026-06-11.md`.
- Required sections:
  - `时间窗口`
  - `本周压缩结论`
  - `Codex 快速审查索引`
  - `按大类概览`
  - `压缩维度诊断`
  - `短期/阶段性记忆中的长期价值提取`
  - `建议动作 / 只读不执行`
  - `上层总结候选 / 不替代原子记忆`
  - candidate-level `不可替代的原子记忆`
  - `短期记忆处理建议`
  - `暂时不压缩 / 不建议写入`
  - `需要用户/Codex确认的问题`
  - `被忽略但可能值得回看的原文`
- Current status: read-only script exists and has been tuned beyond the first inventory version:
  `scripts/weekly_compression_review.py`.
- Manual command for the first run:
  `python -B scripts\weekly_compression_review.py --start-date 2026-06-04 --end-now`
- First generated local report:
  `reports/weekly-compression-2026-06-04-to-2026-06-11.md`
- Current script behavior:
  - reads active memories only for the compression candidate set;
  - outputs `本周压缩结论` before the detailed inventory;
  - outputs `Codex 快速审查索引` so future Codex sessions can inspect the report without asking the user to read every item;
  - diagnoses compression roles inside each broad category, because `memory_category` is only a navigation dimension and not a compression unit;
  - extracts durable long-term value from short-term or stage-specific memory carriers;
  - outputs read-only suggested actions: keep, merge candidate, archive candidate, category-adjustment candidate, and long-term-summary candidate;
  - proposes human-readable candidate durable memories with evidence IDs and readable evidence excerpts;
  - marks irreplaceable atomic memories that should not be covered or archived by a higher-level summary;
  - excludes `临时待办` and `未来产品设想` from automatic long-term summary suggestions;
  - splits temporary handling into real temporary todos versus time/lifecycle mechanism design;
  - lists ignored raw messages that may deserve `学习` or technical records, including raw `156`;
  - never writes new memories or archives old memories automatically.
- Compression rule: weekly compression must be lossless by default. Reusable workflows, preferences, principles, rules, and operational details stay as atomic memories unless the user explicitly confirms a specific low-density duplicate can be archived.
- Compression definition: compression is not replacing many memories with one sentence. It means extracting reusable long-term value from short-term or stage-specific memories while keeping original evidence available.
- Current generated result: the first window report now shows 126 active memories,
  24 ignored raw messages, and 186 interactions.
- Recommended next step: review the generated candidate summaries with the user/Codex. If the structure is useful after one or two real weekly reviews, then add a formal `brain.py weekly-compression` command. Keep automatic write/archive deferred.
- Likely change type: review workflow plus CLI/report code. Do not build a dashboard first.

## Already Changed Or Working Enough For Now

These should not keep reappearing as open work unless new evidence shows failure.

- Normal Feishu text is the memory input path; `?` is the question/retrieval entry. Related memories: `5`, `6`, `105`.
- Symbol shortcuts are now used to avoid command-word collisions: `!`, `#ID`, `-ID`, and `?question`.
- Memory detail lookup by ID is implemented. Related memory: `116`.
- Over-interpretation prompt guard is implemented: factual notes should be stored as facts, not expanded into advice. Related memory: `114`.
- Short-term todo preservation is implemented as a lightweight `临时待办` category, though reminder lifecycle is not complete. Related memories: `120`, `127`.
- Stable `学习` category is implemented for compact concept notes, definitions, distinctions, analogies, and "X 就是 Y" learning records. Raw `156` (`memory+recall就是储存加调取的组合`) should now be preserved as `学习`. Related memories: `139`, `142`, `144`.
- Write-time near-duplicate filtering was strengthened, and a duplicate detail-view memory was archived. Related memories: `73`, `75`, `116`.
- The daily report's automatic Xiaochai-related classification was disabled because it was too noisy. Related memories: `76`, `78`.
- Daily report ignored-message noise was reduced for low-signal tests and later-covered partial inputs.
- Daily report review is now handled through a scoped Codex skill/workflow instead of automatic product classification inside the generated report. Related memory: `141`.
- Weekly Thursday Xiaochai daily-report review now has fixed quality checks for Recall, Duplicate, Over-interpretation, and Category-boundary issues; each check must cite evidence and decide whether to change prompt, change code, or only observe.
- Offline/startup recovery is working well enough in recent real use: messages sent while Xiaochai was offline did not get re-identified unexpectedly after coming back online. Related memories: `45`, `71`, `123`, `128`.

## Do Not Change For Now

These are valid context, principles, or usage notes, but they are not immediate implementation tasks.

- Product positioning: Xiaochai is a personal brain, memory entry, and knowledge-reuse system. Related memories: `2`, `3`, `40`, `60`.
- V0 priority: focus on write stability, semantic recall, evidence-based answers, and Feishu responsiveness before frontend or graph features. Related memories: `41`, `42`.
- Usage and safety notes: send complete sentences when possible, use `?` for questions, and do not send secrets into Feishu. Related memories: `7`, `8`, `9`.
- Resume/project presentation note. Related memory: `38`.
- Embedding and RAG conceptual understanding. Related memories: `82`, `83`.
- Prompt optimization vs model fine-tuning framing. Related memory: `110`.
- Harness as an AI evaluation tool is useful technical knowledge, not a Xiaochai product change by itself. Related memory: `140`.
- The learning-assistant theme-search idea is adjacent to Xiaochai but should not pull the V0 memory system away from stabilization. Related memory: `121`.

## Future Direction

These are good product direction signals, but they should wait until the foundation is stable.

- Model upgrade or professional model direction. Related memories: `26`, `134`.
- "Second me", digital self, and Xiaochai as a broader personal agent. Related memories: `33`, `102`, `104`.
- Agent workflow, autonomous planning/execution/reflection, and Xiaochai Agent roadmap. Related memories: `66`, `85`, `132`, `133`.
- Multi-app capture and observing user behavior across external software. Related memory: `103`.
- More advanced RAG, query planning, stronger retrieval/reranking, and larger architecture upgrades. Related memories: `84`, `85`, `96`, `97`, `138`.
- Weekly or periodic reflective summary is becoming a near-term candidate through the Memory Compression framing, but should start as a small review workflow rather than a large automation. Related memories: `27`, `138`, `145`, `154`, `155`.

## Current Product Judgment

The next best work is not a big new feature. The current order should be:

1. Keep collecting real usage through Feishu.
2. Review raw input versus stored memories manually with Codex when needed.
3. Fix extraction/prompt/category mistakes only when they repeat or affect recall.
4. Verify same-day todo recall through Feishu real use; only add completion/expiry handling if stale todos become a real problem.
5. Verify the new stable `学习` category through real learning notes and daily reports; raw `156` is the baseline example that should no longer be ignored.
6. Continue the small weekly Memory Compression review workflow if the report structure stays useful after review.
7. Revisit Router and read-time dedupe after more retrieval failures are observed.
