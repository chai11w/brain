# Stabilization Log

Project-scoped stabilization log for Xiaochai / AI-native Personal Brain.
Do not ingest this file into Xiaochai's personal memory database.

Purpose:

- Record what was changed during each stabilization pass.
- Record why the change was made.
- Record how to verify whether it worked later.
- Update this file whenever Codex changes Xiaochai based on a daily report review.
- Keep `.agents/project_memory.md` focused on current handoff state instead of daily detail.
- Maintain this file by pruning or compressing entries that are verified and no
  longer useful. Do not let it become an append-only dump.

Maintenance rule:

- Keep failed fixes, active watch items, and decisions that explain current behavior.
- Compress verified fixes into a short note once they have stayed stable for a few report cycles.
- Remove details that are both verified and no longer useful for future debugging.

## Status Labels

- `watch`: change is in place, needs real usage to evaluate.
- `verified`: later reports or manual checks show the change works.
- `failed`: later reports show the change did not solve the problem.
- `superseded`: replaced by a newer approach.

## 2026-06-06

### Daily Report Duplicate Generation Guard

- Status: `watch`
- Problem: the daily report generated once around 10:00 and again around 18:00, likely due to Codex automation time zone handling.
- Change: updated the Codex App automation from UTC hour 10 to UTC hour 2 so it maps to China time 10:00.
- Change: added same-day duplicate protection to `scripts/run_daily_report.ps1`; when a `reports/last-24h-YYYY-MM-DD-*.md` file already exists for the local date, the script skips unless `-Force` is used.
- Verification later: check `.tmp_tests/daily_report_task.log` and `reports/` on the next day. Expected result is one new report around 10:00, with any accidental second trigger logging `skip existing_daily_report=...` instead of generating another file.

## 2026-06-07

### Daily Report Xiaochai Auto-Classification Disabled

- Status: `verified`
- Problem: the daily report's automatic Xiaochai-related review was too broad. General AI notes containing terms such as RAG or agent could be pulled into Xiaochai review, and product-decision notes could be mislabeled as defects.
- Decision: disable the automatic Xiaochai-related review section in `personal_brain/daily_report.py`.
- Reasoning: the report should stay faithful to raw input, stored memories, extraction runs, and interactions. Xiaochai product interpretation is currently higher quality when Codex reviews the database and report with the user each day.
- Follow-up: added `.agents/xiaochai_backlog.md` as the manually maintained place to separate Xiaochai-related memories into recently worth changing, already changed, do-not-change-now, and future direction.
- Verification: `reports/last-24h-2026-06-10-1002.md` no longer contains the `小柴相关复盘分类` section; the report keeps issue markers, raw-to-memory mapping, extraction details, memory details, and interaction details.
- Verification later: check the next generated daily report. Expected result is no `小柴相关复盘分类` section, while `链路问题标记`, `原文 -> 实际存入的记忆`, raw details, extraction details, memory details, and interaction details remain.

### Offline Startup Recovery Observation

- Status: `verified`
- Observation: the user reported that recent messages sent while Xiaochai was offline were not re-identified unexpectedly after Xiaochai came back online.
- Decision: do not treat offline/startup recovery as a near-term code change unless new evidence shows message loss, duplicate processing, or delayed replay.
- Backlog update: moved offline/startup recovery from recently worth changing to already working enough in `.agents/xiaochai_backlog.md`.

### Same-Day Todo Recall Scope

- Status: `watch`
- Clarification: the user does not want scheduled date reminders now.
- Current scope: when the user asks on the day itself, such as `?今天要做什么`, Xiaochai should be able to retrieve relevant same-day or currently active temporary-todo memories.
- Backlog update: renamed the item from temporary todo/date reminder behavior to same-day todo recall in `.agents/xiaochai_backlog.md`.
- Change: added same-day/todo-aware recall boosting in `personal_brain/semantic.py`, prioritizing `临时待办` and task-like memories for today's-task questions.
- Change: added current-date and relative-date guidance to `personal_brain/answer.py`, so yesterday's `明天` can be interpreted as today when answering.
- Verification run: `python -B brain.py recall "今天要做什么" --limit 10` now ranks `临时待办` memories first, including memory `126`, `99`, `98`, and `120`. `python -B brain.py ask "今天要做什么"` answered with concrete todos before product-feature discussion.

### Feishu Symbol Shortcuts

- Status: `watch`
- Problem: Chinese word commands such as `详情 91` or `删除 91` could collide with normal notes the user might want to store.
- Change: added symbol-only Feishu shortcuts in `scripts/feishu_bridge.py`.
- Current shortcuts:
  - normal text: remember/extract
  - `?question` / `？问题`: ask from memory evidence
  - `#91`: show memory detail, raw input, topics, entities, and extraction metadata
  - `-91`: archive memory
  - `!`: show shortcut help
- Verification later: send `!` and `#91` in Feishu. Expected result is shortcut help and a detailed memory view. Send text beginning with `详情` or `删除`; expected result is normal memory handling, not command handling.

### Detail View For Single Memory

- Status: `watch`
- Problem: daily report review showed the user could only see summaries and wanted to inspect a specific memory's original input and full extracted content.
- Change: implemented Feishu detail lookup through `#memory_id`, reusing the existing read-only `memory_show` path.
- Change: expanded the Feishu `#memory_id` reply to include raw source/time, memory type, importance/confidence, topics, entities, topic reasons, and extraction run metadata.
- Verification run: locally formatted `memory 126` through `format_memory_detail_reply`; the reply now includes raw evidence, stored memory, topics/entities, and extraction metadata.
- Verification later: when reviewing a suspicious memory, use `#ID` and check whether the reply is enough to judge extraction quality without opening SQLite or the full Markdown report.

### Near-Duplicate Write-Time Filter Still Leaks

- Status: `superseded`
- Problem: the 2026-06-07 daily report shows `memory 115` and `memory 116` captured the same product request: memory detail should show raw input and full content.
- Current evidence:
  - `memory 115`: "小柴记忆提取需支持查看完整详情"
  - `memory 116`: "小柴记忆提取需支持查看原始输入与完整内容"
- Interpretation: deterministic near-duplicate filtering is not strong enough for short, semantically equivalent project feedback phrased almost identically.
- Superseded by: `Xiaochai Feedback Duplicate Cleanup`, which strengthened Xiaochai feedback duplicate detection and archived duplicate `memory 115`.

### Over-Interpretation In Fact Memories

- Status: `watch`
- Problem: the "享做笔记" example showed Xiaochai turning a simple product defect note into a memory that included advice such as avoiding long lines.
- Change: updated `personal_brain/extractor.py` to `memory-extraction-v5` and added prompt rules that facts, defects, observations, or experiences must be stored faithfully without adding advice, solutions, avoidance actions, or product coaching unless the user explicitly asks.
- Verification later: send a plain defect note. Expected result is a factual memory only, with no extra recommendation.

### Temporary Todo Preservation

- Status: `watch`
- Problem: temporary interview-preparation reminders such as printing a resume and bringing a folder can be ignored because they are not durable long-term memories.
- Change: kept the existing `临时待办` category as the lightweight mechanism instead of adding a full todo schema. Added a fallback in `personal_brain/extractor.py` so ignored-looking explicit short-term reminders are preserved as `临时待办`.
- Verification later: send a short reminder such as `下周二面试前别忘了打印简历`. Expected result is a `临时待办` memory rather than ignored raw input.

### Daily Report Ignored Marker Noise

- Status: `verified`
- Problem: daily report issue markers were noisy because low-signal test messages like `1` and partial messages later superseded by a fuller stored message were counted as problems.
- Change: updated `personal_brain/daily_report.py` so ignored raw messages are not marked as issues when they are low-signal test input or covered by a later nearby raw message that did create a memory.
- Verification run: generated `.tmp_tests/last-24h-2026-06-07-1021.md`; issue markers dropped to `0` for the current window.
- Verification: `reports/last-24h-2026-06-09-1015.md` and `reports/last-24h-2026-06-10-1002.md` both show `issue_markers: 0`; low-signal `1` inputs were ignored without becoming review noise.
- Verification: `reports/last-24h-2026-06-11-1001.md` shows `issue_markers: 1` for raw `156` (`memory+recall就是储存加调取的组合`). This is useful signal rather than noise; it feeds the `学习` category / short concept-note backlog item.

### Xiaochai Review Classification Tuning

- Status: `superseded`
- Problem: the Xiaochai review section put memory lifecycle design, such as short-term/long-term memory decay, under current defects.
- Change: updated `personal_brain/daily_report.py` so memory lifecycle design goes to `near_term_fixes`, while future product shape still goes to `future_directions`.
- Change: added near-term signals such as `需支持`, `希望`, and `避免`, so requests like detail view and avoiding over-interpretation are classified as near-term fixes.
- Superseded by: the automatic Xiaochai review section was disabled. Xiaochai-related product interpretation now belongs in `.agents/xiaochai_backlog.md`, maintained manually after Codex reviews the report/database with the user.

### Xiaochai Feedback Duplicate Cleanup

- Status: `watch`
- Problem: `memory 115` and `memory 116` stored the same detail-view request with different wording.
- Change: strengthened `personal_brain/extractor.py` duplicate detection for same-category Xiaochai product feedback by comparing core intent terms, not only raw text similarity.
- Change: archived duplicate `memory 115`; kept `memory 116` as the active, more precise version.
- Verification run: a candidate equivalent to `memory 115` now matches existing `memory 116` in `find_duplicate_memory`.
- Verification later: repeat a semantically equivalent Xiaochai feedback shortly after an existing one. Expected result is duplicate skip, while raw message and extraction run remain auditable.

### Outdated Feishu Command Memory Cleanup

- Status: `verified`
- Problem: `memory 47` still described the old Chinese-word deletion command after Feishu commands moved to symbols.
- Change: archived `memory 47` so semantic recall no longer returns the outdated `删除+id` command.
- Current command memory should prefer the README and active behavior: normal text remembers, `?` asks, `#ID` shows detail, `-ID` archives, and `!` shows help.

## 2026-06-13

### Learning Category For Compact Concept Notes

- Status: `watch`
- Problem: recent learning notes increased, and the 2026-06-11 daily report showed raw `156` (`memory+recall就是储存加调取的组合`) was ignored. This suggested compact concept-definition notes could be lost unless the user phrased them as obviously durable.
- Change: added stable `学习` to `MEMORY_CATEGORIES`, updated extraction prompt rules, normalized learning aliases, and added a deterministic fallback that preserves ignored-looking reusable concept notes as `学习`.
- Boundary: `学习` is for compact concepts, definitions, distinctions, analogies, and "X 就是 Y" learning notes. Technical judgments remain `技术思考`; workflows remain `工作流方法`; direct Xiaochai changes remain `现有项目改进`; user self-knowledge remains `自身认知更新`.
- Verification later: send examples such as `memory+recall就是储存加调取的组合`, `长期记忆就是未来大概率会重复利用的信息`, and `今天晚上去吃烧烤`. Expected result: the first two become `学习`; the dinner fragment is ignored unless it has a real todo/time context.

## Future Backlog From Xiaochai Memories

These are intentionally stored as future direction notes, not immediate work.

- Memory lifecycle: design short-term vs long-term memory behavior, including decay, retrieval-use lowering, expiration, and superseded memories.
- Advanced RAG: revisit query planning RAG or stronger retrieval/reranking when the current embedding recall becomes the bottleneck.
- Read-time dedupe: add evidence dedupe during ask/recall so repeated memories do not crowd out diverse evidence.
- Multi-app capture: later explore connecting Xiaochai to broader software behavior, such as browser/app favorites or collected content, after the Feishu memory foundation is stable.
- Weekly reflective review: revisit periodic synthesis once daily extraction, duplicate handling, detail lookup, and answer quality are stable.
