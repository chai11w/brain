---
name: xiaochai-daily-review-c
description: Use when the user asks to review specified Xiaochai reports, daily reports, recent Xiaochai memory records, raw message ranges, memory ranges, or Xiaochai-related stored content; compare raw inputs with stored memories and interactions; judge extraction quality; identify Xiaochai-related feedback; classify items as fix now, already handled, do not change now, future direction, or knowledge-only; extract Xiaochai improvement/problem/experience items and generate a small daily foundation-improvement proposal.
---

# Xiaochai Daily Review

Use this skill when the user asks to review a specific Xiaochai report, date range, recent reports, raw message range, memory range, or Xiaochai-related records.

The skill is a narrow review workflow. It is not a project onboarding skill, not an automatic product classifier, and not a license to make broad code changes.

## Scope

Review only the range the user specifies.

Valid scopes include:

- today, yesterday, the last two days, or another date range
- one or more files under `reports/`
- a raw message range such as `raw_message_id 123-149`
- a memory range such as `memory_id 120-140`
- Xiaochai-related records the user explicitly asks about

Do not assume the target is always the latest 24 hours.

Do not automatically read the whole project context. Read project context only if it is needed to decide whether something was already fixed, deferred, or belongs in the backlog.

## Main Job

Turn the specified evidence into a clear review:

1. What the user originally entered.
2. What Xiaochai stored.
3. Whether the stored memory is faithful and useful.
4. Whether the category/topic is reasonable.
5. Whether any Xiaochai-related content needs action.
6. Which items are already handled, do not need changes now, or belong to future direction.
7. Extract Xiaochai improvement/problem/direction items from the reviewed
   evidence and turn them into a small, prioritized improvement proposal.

The review must not stop at describing storage quality. When the specified
range contains Xiaochai-related improvement notes, defects, product questions,
workflow ideas, recall/answer problems, report feedback, Feishu/startup issues,
or memory-quality concerns, synthesize them into an actionable plan.

Hard rule: if the reviewed range contains any Xiaochai-related record, the
output must include a `今日小柴基体优化方案`. Do not answer only "storage quality
looks good" or "no code change needed" unless you also explain the extracted
Xiaochai items and why the proposal is observation-only.

## Evidence

Use the minimum evidence needed:

- specified report files under `reports/`
- matching rows from `raw_messages`
- matching rows from `memories`
- matching rows from `interaction_logs`
- `.agents/xiaochai_backlog.md` only when classifying Xiaochai product items
- `.agents/stabilization_log.md` only when checking whether something was already changed or verified

Do not read `README.md`, `ARCHITECTURE.md`, or broad project docs unless the user asks or the decision needs architecture context.

## Review Workflow

1. Determine the target range from the user's request.
   If the range is unclear, infer conservatively from words such as "today", "yesterday", "last two days", "this report", or explicit IDs.

2. Read the relevant report or database rows.
   Do not rely only on a report summary when the database can clarify the raw input and stored memory.

3. Compare raw input with stored memory.
   Check:
   - raw message content
   - processed status
   - generated memory content
   - memory category
   - memory status
   - interaction reply, if relevant

   If an older report contains a generated section named `小柴相关复盘分类`,
   treat it only as a historical hint. Do not trust its bucket labels as the
   review result. Reclassify Xiaochai-related items manually using the rules in
   this skill, because that automatic section was intentionally removed after it
   proved too broad.

4. Judge storage quality.
   Look for:
   - should-have-stored but ignored
   - should-have-ignored but stored
   - over-interpretation or advice invented by the model
   - memory split too finely
   - wrong category or topic
   - duplicate or outdated memories
   - temporary todos not stored as `临时待办`
   - ask/detail/archive command problems
   - answer recall using the wrong evidence
   - stale Feishu events that might hide a replay or missed-processing issue

   When `interaction_logs.action` is `stale_ignored`, do not immediately count it
   as message loss. First check whether the same user text was already processed
   in a previous raw message or previous report window. If it was already stored,
   classify the stale event as delayed retry protection working correctly. If it
   was not stored and the content was meaningful, treat it as a startup/offline
   watch item.

   For Thursday weekly Xiaochai daily-report reviews, always include a fixed
   four-part memory-quality audit. Use the same structure for other larger
   report windows when useful:

   - `Recall问题`
   - `Duplicate问题`
   - `Over-interpretation问题`
   - `Category边界问题`

   Each quality class must state:

   - `是否发生`: yes/no/unclear, based on report/database evidence.
   - `例子`: raw_message, memory_id, and/or interaction id. If none occurred,
     write `无明确例子`.
   - `处理判断`: choose one of `改prompt`, `改代码`, or `仅观察`, with a short
     reason.

5. Identify Xiaochai-related content manually.
   Do not classify something as Xiaochai-related only because it mentions broad technical words like RAG, agent, embedding, retrieval, prompt, or workflow. Check whether the text is actually about Xiaochai, the memory box, daily reports, Feishu entry, memory quality, recall, answer behavior, startup, or product direction.

6. Classify Xiaochai-related items.
   Use these buckets:
   - `最近要改`: affects current use and the failure is clear
   - `已经改了/够用`: already implemented, verified, or works well enough in real use
   - `暂时不改`: valid context or idea, but not the current bottleneck
   - `未来方向`: product direction for later stages
   - `只是知识记录`: useful knowledge, not a Xiaochai product request

7. Generate a Xiaochai improvement proposal.
   If the reviewed range contains Xiaochai-related records, output a concrete
   `今日小柴基体优化方案`. This section is mandatory even when the final decision is
   "do not change code today".

   The proposal must include:
   - `提取出的小柴改进/问题`: evidence items, including raw/memory/interaction IDs
   - `用户真实体验问题`: the underlying user pain, confusion, desire, or workflow friction
   - `推荐改进方案`: the recommended product/technical response
   - `最小实现`: the smallest useful implementation or review step
   - `暂时不做`: adjacent ideas or larger features to avoid for now
   - `验证方式`: how to verify later through reports, Feishu, CLI, or database checks

   The proposal should be small and prioritized. Prefer one or two foundation
   improvements over a broad roadmap. If the evidence only contains future
   direction, say that no immediate code change is recommended and explain what
   evidence would make it actionable.

8. Decide the action.
   Possible actions:
   - change code
   - change prompt or extraction rules
   - archive duplicate or outdated memories
   - update `.agents/xiaochai_backlog.md`
   - update `.agents/stabilization_log.md`
   - ask the user to test in Feishu
   - continue observing
   - do nothing for now

   If report evidence verifies a stabilization item currently marked `watch`,
   update `.agents/stabilization_log.md` to `verified` and include the report
   file or database evidence used for verification.

## Decision Rules

Do not turn every Xiaochai-related note into a feature.

If any Xiaochai-related record exists in the reviewed range, always produce a
`今日小柴基体优化方案`. If no immediate implementation is recommended, the proposal
must still say what to observe next and what evidence would justify action.

For relative date requests such as "前两天", "昨天", or "今天", state the exact
calendar dates used in the review before giving conclusions.

Prefer this order:

1. Verify with evidence.
2. Make the smallest useful fix.
3. Update the relevant MD files when a product judgment or stabilization result changes.

Avoid starting:

- scheduled reminder systems
- frontend work
- GraphRAG
- full task manager
- large architecture upgrades
- broad automatic Xiaochai classification

If something already works in real use, mark it as working enough and stop treating it as active work.

If something is product direction but not the current bottleneck, classify it as future direction.

## Output

Answer in Chinese.

Use this shape unless the user asks for a different format:

```text
范围：
这次看的是……

整体判断：
记录和存储质量总体……

原文 -> 记忆质量：
1. raw xxx：……
2. raw xxx：……

固定四类质量审查：
Recall问题：
- 是否发生：是/否/不明确
- 例子：memory_id/raw_message/interaction ……；没有则写“无明确例子”
- 处理判断：改prompt / 改代码 / 仅观察；理由：……
Duplicate问题：
- 是否发生：……
- 例子：……
- 处理判断：……
Over-interpretation问题：
- 是否发生：……
- 例子：……
- 处理判断：……
Category边界问题：
- 是否发生：……
- 例子：……
- 处理判断：……

小柴相关判断：
- 最近要改：……
- 已经改了/够用：……
- 暂时不改：……
- 未来方向：……
- 只是知识记录：……

提取出的改进/问题：
1. 证据：raw/memory/interaction xxx；问题：……；判断：……
2. ……

今日小柴基体优化方案：
提取出的小柴改进/问题：
1. 证据：raw/memory/interaction xxx；……
用户真实体验问题：……
推荐改进方案：……
最小实现：……
暂时不做：……
验证方式：……

今天建议：
1. ……
2. ……

需要更新的文件：
- .agents/xiaochai_backlog.md：……
- .agents/stabilization_log.md：……
```

If code was changed, include verification commands and results. If no code change is recommended, say that clearly.
