from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from personal_brain.config import load_config  # noqa: E402


@dataclass(frozen=True)
class MemoryRow:
    id: int
    raw_message_id: int
    created_at: str
    updated_at: str
    title: str
    category: str
    memory_type: str
    importance: float
    confidence: float
    status: str
    content: str
    raw_content: str
    topics: list[str]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a read-only weekly memory compression review")
    parser.add_argument("--config", default="config.json", help="config file path")
    parser.add_argument("--start-date", help="YYYY-MM-DD; defaults to --last-days window")
    parser.add_argument("--end-date", help="YYYY-MM-DD; exclusive end date unless --end-now is used")
    parser.add_argument("--last-days", type=int, default=7, help="window length when --start-date is omitted")
    parser.add_argument("--end-now", action="store_true", help="end at current local time")
    parser.add_argument("--output-dir", default="reports", help="directory for local Markdown reports")
    parser.add_argument("--print-path-only", action="store_true", help="only print the output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    args = build_parser().parse_args(argv)
    start_at, end_at = resolve_window(args)

    config = load_config(args.config)
    db_path = config.database_path
    if not db_path.exists():
        print(f"warning: database not found: {db_path}")
        return 1

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        memories = load_memories(conn, start_at, end_at)
        raw_ignored = load_ignored_raw_messages(conn, start_at, end_at)
        interactions = load_interactions(conn, start_at, end_at)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name(start_at, end_at)
    markdown = format_review(
        start_at=start_at,
        end_at=end_at,
        memories=memories,
        raw_ignored=raw_ignored,
        interactions=interactions,
    )
    output_path.write_text(markdown + "\n", encoding="utf-8")

    if args.print_path_only:
        print(output_path)
        return 0
    print(f"weekly compression review: {output_path}")
    print(f"start_at: {fmt(start_at)}")
    print(f"end_at: {fmt(end_at)}")
    print(f"active_memories: {len(memories)}")
    print(f"ignored_raw_messages: {len(raw_ignored)}")
    print(f"interactions: {len(interactions)}")
    return 0


def resolve_window(args: argparse.Namespace) -> tuple[datetime, datetime]:
    if args.end_now:
        end_at = datetime.now()
    elif args.end_date:
        end_at = datetime.strptime(args.end_date, "%Y-%m-%d")
    else:
        end_at = datetime.now()

    if args.start_date:
        start_at = datetime.strptime(args.start_date, "%Y-%m-%d")
    else:
        if args.last_days <= 0:
            raise ValueError("--last-days must be positive")
        start_at = end_at - timedelta(days=args.last_days)
    if start_at >= end_at:
        raise ValueError("start time must be before end time")
    return start_at, end_at


def output_name(start_at: datetime, end_at: datetime) -> str:
    return f"weekly-compression-{start_at:%Y-%m-%d}-to-{end_at:%Y-%m-%d}.md"


def load_memories(conn: sqlite3.Connection, start_at: datetime, end_at: datetime) -> list[MemoryRow]:
    rows = conn.execute(
        """
        SELECT
            m.id, m.raw_message_id, m.created_at, m.updated_at, m.title,
            m.memory_category, m.memory_type, m.importance, m.confidence,
            m.status, m.content, r.content AS raw_content
        FROM memories m
        JOIN raw_messages r ON r.id = m.raw_message_id
        WHERE m.created_at >= ? AND m.created_at < ?
          AND m.status = 'active'
        ORDER BY m.memory_category, m.created_at, m.id
        """,
        (fmt(start_at), fmt(end_at)),
    ).fetchall()
    memories: list[MemoryRow] = []
    for row in rows:
        memory_id = int(row["id"])
        memories.append(
            MemoryRow(
                id=memory_id,
                raw_message_id=int(row["raw_message_id"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                title=row["title"] or "",
                category=row["memory_category"],
                memory_type=row["memory_type"],
                importance=float(row["importance"]),
                confidence=float(row["confidence"]),
                status=row["status"],
                content=row["content"],
                raw_content=row["raw_content"],
                topics=topics_for_memory(conn, memory_id),
            )
        )
    return memories


def topics_for_memory(conn: sqlite3.Connection, memory_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT t.name
        FROM memory_topics mt
        JOIN topics t ON t.id = mt.topic_id
        WHERE mt.memory_id = ?
        ORDER BY mt.confidence DESC, t.name ASC
        """,
        (memory_id,),
    ).fetchall()
    return [str(row["name"]) for row in rows]


def load_ignored_raw_messages(conn: sqlite3.Connection, start_at: datetime, end_at: datetime) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT id, created_at, source, sender, processed_status, content
            FROM raw_messages
            WHERE created_at >= ? AND created_at < ?
              AND processed_status = 'ignored'
            ORDER BY created_at, id
            """,
            (fmt(start_at), fmt(end_at)),
        ).fetchall()
    ]


def load_interactions(conn: sqlite3.Connection, start_at: datetime, end_at: datetime) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT id, created_at, action, status, raw_message_id, user_text, reply_text
            FROM interaction_logs
            WHERE created_at >= ? AND created_at < ?
            ORDER BY created_at, id
            """,
            (fmt(start_at), fmt(end_at)),
        ).fetchall()
    ]


def format_review(
    *,
    start_at: datetime,
    end_at: datetime,
    memories: list[MemoryRow],
    raw_ignored: list[dict[str, Any]],
    interactions: list[dict[str, Any]],
) -> str:
    by_category: dict[str, list[MemoryRow]] = defaultdict(list)
    for memory in memories:
        by_category[memory.category].append(memory)

    lines = [
        "# 小柴周度 Memory Compression Review",
        "",
        "用途：只读审查最近一段时间的 active 记忆，从短期/阶段性材料里提取可长期复用的内容；不写数据库，不自动归档。",
        "提醒：本报告是 Memory Compression 的人工审查材料。候选内容需要用户/Codex确认后，才能进入长期记忆或触发归档。",
        "",
        "## 时间窗口",
        "",
        f"- start_at: {fmt(start_at)}",
        f"- end_at: {fmt(end_at)}",
        f"- active_memories: {len(memories)}",
        f"- ignored_raw_messages: {len(raw_ignored)}",
        f"- interactions: {len(interactions)}",
        "",
        "## 本周压缩结论",
        "",
    ]
    append_weekly_conclusions(lines, by_category, raw_ignored)
    lines.extend(["", "## Codex 快速审查索引", ""])
    append_codex_review_index(lines, memories, raw_ignored)
    lines.extend(["", "## 按大类概览", ""])
    append_category_overview(lines, by_category)
    lines.extend(["", "## 压缩维度诊断", ""])
    append_compression_dimension_diagnosis(lines, by_category)
    lines.extend(["", "## 短期/阶段性记忆中的长期价值提取", ""])
    append_durable_value_extractions(lines, memories)
    lines.extend(["", "## 上层总结候选 / 不替代原子记忆", ""])
    append_summary_candidates(lines, by_category)
    lines.extend(["", "## 短期记忆处理建议", ""])
    append_temporary_memory_review(lines, memories, end_at)
    lines.extend(["", "## 暂时不压缩 / 不建议写入", ""])
    append_do_not_compress(lines, by_category)
    lines.extend(["", "## 需要用户/Codex确认的问题", ""])
    append_confirmation_questions(lines, memories, raw_ignored)
    lines.extend(["", "## 被忽略但可能值得回看的原文", ""])
    append_ignored_raw(lines, raw_ignored)
    return "\n".join(lines).rstrip()


def append_codex_review_index(
    lines: list[str],
    memories: list[MemoryRow],
    raw_ignored: list[dict[str, Any]],
) -> None:
    role_groups: dict[str, list[MemoryRow]] = defaultdict(list)
    for row in memories:
        role_groups[compression_role(row)].append(row)
    concept_ignored = [row for row in raw_ignored if maybe_concept_note(str(row["content"]))]

    lines.extend(
        [
            "- 阅读方式：这份报告主要给 Codex/审查者看；先读本索引，再按需跳到后文证据。",
            "- 压缩定义：从短期/阶段性载体里提取长期价值，不是用一句话替换多条原子记忆。",
            f"- 绝不直接归档：`长期原子/应保留` {len(role_groups.get('长期原子/应保留', []))} 条，尤其是工作流、使用规则、偏好、原则。",
            f"- 优先提取长期价值：`机制设计/可总结但保留证据` {len(role_groups.get('机制设计/可总结但保留证据', []))} 条，`项目改进候选/可汇总` {len(role_groups.get('项目改进候选/可汇总', []))} 条。",
            f"- 单独确认短期状态：`短期/待确认` {len(role_groups.get('短期/待确认', []))} 条，只确认完成/过期，不自动删除。",
            f"- 只做方向观察：`未来方向/不压成承诺` {len(role_groups.get('未来方向/不压成承诺', []))} 条，不转成近期路线图。",
            f"- 学习候选：`知识概念/学习候选` {len(role_groups.get('知识概念/学习候选', []))} 条；ignored raw 里另有 {len(concept_ignored)} 条短概念信号。",
            "- Codex 下一步：优先审查 `短期/阶段性记忆中的长期价值提取` 是否真的提取出可复用规则；不要要求用户逐条读完整报告。",
        ]
    )


def append_weekly_conclusions(
    lines: list[str],
    by_category: dict[str, list[MemoryRow]],
    raw_ignored: list[dict[str, Any]],
) -> None:
    total = sum(len(rows) for rows in by_category.values())
    project_count = len(by_category.get("现有项目改进", []))
    temp_count = len(by_category.get("临时待办", []))
    future_count = len(by_category.get("未来产品设想", []))
    concept_ignored = [row for row in raw_ignored if maybe_concept_note(str(row["content"]))]

    if total == 0:
        lines.append("- 本窗口没有 active 记忆，暂不适合做压缩。")
        return

    if project_count:
        lines.append(
            f"- 本窗口的核心不是普通周报展示，而是小柴基体优化：`现有项目改进` 有 {project_count} 条 active 记忆，应该优先压缩成少量稳定原则和下一步方案。"
        )
    lines.append("- `memory_category` 只能作为导航维度，不能直接作为压缩单位；同一大类里同时可能有长期可复用规则、短期待办、机制设计、未来方向和低密度观察。")
    top_categories = sorted(by_category.items(), key=lambda item: (-len(item[1]), item[0]))[:3]
    top_text = "；".join(f"{category} {len(rows)} 条" for category, rows in top_categories)
    lines.append(f"- 本周主要记忆分布：{top_text}。压缩时应先处理高密度大类，低密度大类只观察。")

    lifecycle_rows = find_rows_by_keywords(
        [row for rows in by_category.values() for row in rows],
        ("短期", "临时", "待办", "过期", "归档", "衰减", "压缩", "周报", "weekly", "Memory Compression"),
    )
    if lifecycle_rows:
        lines.append(
            f"- 短期记忆生命周期已经成为真实设计问题：找到 {len(lifecycle_rows)} 条相关记忆。周报应同时给出“可归档/待确认”和“机制设计保留”两种判断。"
        )
    elif temp_count:
        lines.append(f"- 有 {temp_count} 条临时待办需要人工确认是否仍有效，但暂时不自动删除。")

    if concept_ignored:
        examples = ", ".join(f"raw {row['id']}" for row in concept_ignored[:3])
        lines.append(
            f"- 被忽略原文里有短概念信号（{examples}），说明 `学习` 大类仍有价值；但本报告只提出证据，不直接改分类规则。"
        )

    if future_count:
        lines.append(
            f"- `未来产品设想` 有 {future_count} 条，适合保留为方向素材，不建议在第一版压成路线图，避免把愿景过早固化成执行承诺。"
        )


def append_category_overview(lines: list[str], by_category: dict[str, list[MemoryRow]]) -> None:
    if not by_category:
        lines.append("- none")
        return
    for category, rows in sorted(by_category.items(), key=lambda item: (-len(item[1]), item[0])):
        topic_counts = Counter(topic for row in rows for topic in row.topics)
        top_topics = "、".join(topic for topic, _ in topic_counts.most_common(6)) or "无主题"
        lines.extend([f"### {category}", "", f"- 数量：{len(rows)}", f"- 高频主题：{top_topics}", ""])
        for row in sorted(rows, key=lambda item: (-item.importance, item.id))[:8]:
            lines.append(
                f"- memory {row.id} / raw {row.raw_message_id} / {row.memory_type} / importance={row.importance:.2f}: {row.title or short(row.content, 36)}"
            )
        if len(rows) > 8:
            lines.append(f"- 另有 {len(rows) - 8} 条未展开。")
        lines.append("")


def append_compression_dimension_diagnosis(lines: list[str], by_category: dict[str, list[MemoryRow]]) -> None:
    if not by_category:
        lines.append("- none")
        return
    lines.append("原则：大类只负责导航；压缩时先看每条记忆的复用价值和生命周期。")
    lines.append("")
    for category, rows in sorted(by_category.items(), key=lambda item: (-len(item[1]), item[0])):
        role_groups: dict[str, list[MemoryRow]] = defaultdict(list)
        for row in rows:
            role_groups[compression_role(row)].append(row)
        role_text = "；".join(
            f"{role} {len(role_rows)} 条"
            for role, role_rows in sorted(
                role_groups.items(),
                key=lambda item: (compression_role_order(item[0]), item[0]),
            )
        )
        lines.extend([f"### {category}", "", f"- 压缩角色分布：{role_text}"])
        for role, role_rows in sorted(
            role_groups.items(),
            key=lambda item: (compression_role_order(item[0]), item[0]),
        ):
            examples = sorted(role_rows, key=lambda item: (-item.importance, item.id))[:3]
            example_text = "；".join(f"memory {row.id} {row.title or short(row.content, 28)}" for row in examples)
            lines.append(f"- {role} 示例：{example_text}")
        lines.append("")


def compression_role(row: MemoryRow) -> str:
    if row.category == "临时待办" or (looks_temporary(row) and not looks_memory_lifecycle_design(row)):
        return "短期/待确认"
    if row.category == "未来产品设想":
        return "未来方向/不压成承诺"
    if row.category in {"工作流方法", "产品使用技巧", "信息安全"} and should_preserve_as_atomic(row):
        return "长期原子/应保留"
    if row.category in {"学习", "技术思考"}:
        return "知识概念/学习候选"
    if row.category in {"自身认知更新", "生活感悟"}:
        return "长期自我认知/可复用"
    if looks_memory_lifecycle_design(row):
        return "机制设计/可总结但保留证据"
    if should_preserve_as_atomic(row):
        return "长期原子/应保留"
    if row.category == "现有项目改进":
        return "项目改进候选/可汇总"
    return "低密度/观察"


def compression_role_order(role: str) -> int:
    order = {
        "长期原子/应保留": 0,
        "机制设计/可总结但保留证据": 1,
        "项目改进候选/可汇总": 2,
        "长期自我认知/可复用": 3,
        "知识概念/学习候选": 4,
        "短期/待确认": 5,
        "未来方向/不压成承诺": 6,
        "低密度/观察": 7,
    }
    return order.get(role, 99)


def append_durable_value_extractions(lines: list[str], memories: list[MemoryRow]) -> None:
    candidates = build_durable_value_extractions(memories)
    if not candidates:
        lines.append("- 暂无明显可从短期/阶段性记忆中提取的长期价值。")
        return
    lines.append("原则：压缩不是“多条换一句话”，而是从短期载体里抽出可长期复用的原则、流程、偏好、概念或机制判断；原子记忆默认保留。")
    lines.append("")
    for index, item in enumerate(candidates, start=1):
        row = item["row"]
        lines.extend(
            [
                f"### {index}. memory {row.id}: {row.title or short(row.content, 48)}",
                "",
                f"- raw: {row.raw_message_id}",
                f"- 原大类/类型：{row.category} / {row.memory_type}",
                f"- 压缩角色：{item['role']}",
                f"- 短期或阶段性载体：{short(row.content, 180)}",
                "- 可长期提取的内容：",
                "",
                fenced(item["durable_value"]),
                "",
                f"- 原记忆处理建议：{item['source_action']}",
                "",
            ]
        )


def build_durable_value_extractions(memories: list[MemoryRow]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in memories:
        role = compression_role(row)
        durable_value = durable_value_from_row(row, role)
        if not durable_value:
            continue
        items.append(
            {
                "row": row,
                "role": role,
                "durable_value": durable_value,
                "source_action": durable_source_action(role),
            }
        )
    items.sort(key=lambda item: (durable_role_order(item["role"]), -item["row"].importance, item["row"].id))
    return items[:18]


def durable_value_from_row(row: MemoryRow, role: str) -> str:
    title = row.title or short(row.content, 40)
    content = short(row.content, 220)
    if role == "短期/待确认":
        if has_reusable_signal(row):
            return f"这条短期记忆可作为任务生命周期样本：`{title}`。长期价值不在具体日期，而在它暴露出的待办记录、截止时间、完成确认或复盘需求。"
        return ""
    if role == "机制设计/可总结但保留证据":
        return f"可长期保存为小柴机制设计证据：{content}"
    if role == "项目改进候选/可汇总":
        return f"可长期保存为小柴改进方向：{content}"
    if role == "未来方向/不压成承诺":
        return f"可长期保存为未来方向信号，但不压成近期承诺：{content}"
    if role == "知识概念/学习候选":
        return f"可长期保存为学习/技术概念：{content}"
    if role == "长期自我认知/可复用":
        return f"可长期保存为用户自我认知：{content}"
    if role == "低密度/观察" and has_reusable_signal(row):
        return f"可先作为低置信长期候选观察：{content}"
    return ""


def durable_source_action(role: str) -> str:
    if role == "短期/待确认":
        return "原短期记忆继续等待用户确认完成/过期；只提取长期价值，不自动归档。"
    if role == "未来方向/不压成承诺":
        return "保留原愿景记录；长期价值只作为方向信号，不转成近期路线图。"
    if role == "机制设计/可总结但保留证据":
        return "保留原机制设计证据；长期提取只作为更稳定的索引。"
    return "保留原子记忆；长期提取需要用户/Codex确认后才可写入。"


def durable_role_order(role: str) -> int:
    order = {
        "机制设计/可总结但保留证据": 0,
        "项目改进候选/可汇总": 1,
        "知识概念/学习候选": 2,
        "长期自我认知/可复用": 3,
        "短期/待确认": 4,
        "未来方向/不压成承诺": 5,
        "低密度/观察": 6,
    }
    return order.get(role, 99)


def has_reusable_signal(row: MemoryRow) -> bool:
    text = f"{row.title}\n{row.content}\n{row.raw_content}"
    return any(
        term in text
        for term in (
            "学习",
            "复盘",
            "验证",
            "流程",
            "方法",
            "规则",
            "机制",
            "设计",
            "小柴",
            "Codex",
            "Skill",
            "skills",
            "记忆",
        )
    )


def append_summary_candidates(lines: list[str], by_category: dict[str, list[MemoryRow]]) -> None:
    candidates = build_summary_candidates(by_category)
    if not candidates:
        lines.append("- 暂无明显候选压缩组。")
        return
    for index, candidate in enumerate(candidates, start=1):
        rows = candidate["rows"]
        evidence = ", ".join(f"memory {row.id}/raw {row.raw_message_id}" for row in rows[:8])
        lines.extend(
            [
                f"### {index}. {candidate['title']}",
                "",
                f"- 建议大类：{candidate['category']}",
                f"- 证据：{evidence}",
                f"- 为什么压缩：{candidate['reason']}",
                "- 证据明细（用于人工审查）：",
                "",
            ]
        )
        append_candidate_evidence_details(lines, rows[:8])
        append_irreplaceable_evidence(lines, rows[:8])
        lines.extend(
            [
                "",
                "- 候选长期记忆草案：",
                "",
                fenced(candidate["draft"]),
                "",
                f"- 原记忆处理建议：{candidate['source_action']}",
                "- 审查判断：默认不写库、不归档原子证据；用户/Codex 需要先确认这条总结是否准确、是否值得进入长期记忆、是否只是项目文档状态。",
                "",
            ]
        )


def append_candidate_evidence_details(lines: list[str], rows: list[MemoryRow]) -> None:
    for row in rows:
        lines.extend(
            [
                f"- memory {row.id} / raw {row.raw_message_id} / {row.category} / {row.memory_type} / importance={row.importance:.2f}",
                f"  - 压缩角色：{compression_role(row)}",
                f"  - title: {row.title or '(无标题)'}",
                f"  - memory: {short(row.content, 140)}",
                f"  - raw: {short(row.raw_content, 140)}",
            ]
        )


def append_irreplaceable_evidence(lines: list[str], rows: list[MemoryRow]) -> None:
    preserved = [row for row in rows if should_preserve_as_atomic(row)]
    if not preserved:
        return
    lines.extend(["", "- 不可替代的原子记忆（不要被本总结覆盖或归档）：", ""])
    for row in preserved:
        reason = atomic_preserve_reason(row)
        lines.append(f"  - memory {row.id}: {row.title or short(row.content, 48)}")
        lines.append(f"    - 保留原因：{reason}")


def should_preserve_as_atomic(row: MemoryRow) -> bool:
    text = f"{row.title}\n{row.content}\n{' '.join(row.topics)}"
    if row.memory_type in {"preference", "principle", "decision"}:
        return True
    if row.category in {"工作流方法", "产品使用技巧", "信息安全"}:
        return True
    return any(term in text for term in ("怎么", "步骤", "流程", "规则", "习惯", "使用", "启动", "提问", "记录方式", "不要", "需要"))


def atomic_preserve_reason(row: MemoryRow) -> str:
    if row.category == "工作流方法":
        return "这是可复用流程，后续提问“怎么做”时需要直接召回。"
    if row.category == "产品使用技巧":
        return "这是具体使用规则或操作经验，压缩总结不能替代细节。"
    if row.memory_type in {"preference", "principle", "decision"}:
        return "这是偏好/原则/决策类原子记忆，压缩只能建立上层索引。"
    return "这条包含可操作细节，先保留原子记忆。"


def build_summary_candidates(by_category: dict[str, list[MemoryRow]]) -> list[dict[str, Any]]:
    eligible_rows = [
        row
        for rows in by_category.values()
        for row in rows
        if row.category not in {"临时待办", "未来产品设想"} and row.status == "active"
    ]
    theme_definitions = [
        {
            "title": "小柴日报审查机制升级",
            "category": "现有项目改进",
            "keywords": ("日报", "daily", "报告", "复盘", "skill", "Skill", "体验问题", "改进方案"),
            "draft": "用户已经明确：小柴日报审查的价值不是只判断“存得不错”，而是减少每天重复指挥 Codex 的成本。日报审查应该主动提取小柴改进/问题、用户真实体验问题，并输出推荐改进方案、最小实现、暂时不做和验证方式。",
            "reason": "多条记录都指向日报/Skill 从“审查材料”升级为“基体优化入口”。",
        },
        {
            "title": "周度记忆压缩流程成型",
            "category": "现有项目改进",
            "keywords": ("周报", "weekly", "Memory Compression", "压缩", "长期总结", "短期记忆", "长期记忆"),
            "draft": "Weekly Memory Compression Review 的目标是把最近一周短期记忆中有长期价值的部分压缩成候选长期记忆，同时列出过期或待确认的短期记忆。压缩是建立上层索引和稳定总结，不等于替代原子记忆；可复用流程、偏好、规则和操作细节默认保留。第一版应该只读数据库、生成审查报告、交给用户/Codex确认，不直接写库或自动归档。",
            "reason": "相关记录已经从想法变成可执行流程，适合作为长期项目规则保存。",
        },
        {
            "title": "短期记忆生命周期边界",
            "category": "现有项目改进",
            "keywords": ("短期", "临时", "待办", "过期", "归档", "删除", "衰减", "生命周期", "截止"),
            "draft": "小柴需要区分真正的临时待办和关于短期记忆机制的产品设计。真正临时待办可以在完成、过期或被长期总结吸收后归档；而关于过期、衰减、提醒、压缩的机制设计不应被当作过期待办删除。",
            "reason": "同一批记录里同时出现了临时事项和机制设计，必须拆开处理，避免误归档。",
        },
        {
            "title": "小柴产品定位与当前边界",
            "category": "现有项目改进",
            "keywords": ("个人上下文", "个人脑", "第二大脑", "知识复用", "产品定位", "基体", "AI-native Personal Brain"),
            "draft": "小柴当前更像 AI-native Personal Brain 的记忆与上下文底座，而不是传统笔记、固定文件夹或普通 CRUD 工具。当前阶段应优先稳定原始输入保存、AI 记忆提取、语义召回、证据回答、日报审查和记忆压缩，而不是过早扩展前端、图谱或大型自动化。",
            "reason": "这一主题贯穿多条高重要度记录，是后续取舍的核心边界。",
        },
        {
            "title": "记忆提取与检索质量闭环",
            "category": "现有项目改进",
            "keywords": ("提取", "检索", "召回", "recall", "RAG", "证据", "embedding", "详情", "原始输入", "ignored"),
            "draft": "小柴的稳定性不只看是否存入，还要看原始输入、AI 提取、分类、语义召回、证据回答和日报审查是否形成闭环。被忽略但可能有价值的短概念、重复记忆、召回噪音和缺少原文详情，都应通过报告审查逐步反馈到提取与检索规则。",
            "reason": "多条记录都在描述从写入到召回再到审查的质量闭环。",
        },
        {
            "title": "Codex 作为长期协作层",
            "category": "产品使用技巧",
            "keywords": ("Codex", "项目记忆", "Markdown", "插件", "Product Design", "Skill", "skills"),
            "draft": "Codex 在这个项目中不是一次性执行器，而是小柴基体优化的长期协作层。有效使用方式包括：新对话显式指定项目记忆，让 Markdown 项目上下文承接状态，把日报/周报交给 Codex 审查，并把稳定结论回写到项目文档或技能规则中。这条总结只作为上层索引，不替代“开启新项目时先和 ChatGPT 讨论方案，再结合 project bootstrap skills 交给 AI 执行”等具体工作流记忆。",
            "reason": "本周形成了多条关于 Codex、项目记忆和技能协作的使用经验，可以压缩成稳定用法。",
        },
        {
            "title": "用户与 AI 的分工方式",
            "category": "自身认知更新",
            "keywords": ("灵感", "汗水", "创造力", "成长", "急躁", "失败", "结果", "AI时代"),
            "draft": "用户更擅长发现问题、提出方向和给出灵感，AI 更适合承担整理、执行、验证和反复打磨。当前协作应帮助用户区分目标、假设和方案，把想法落到可验证的小步骤里，而不是让想象速度超过验证速度。",
            "reason": "多条自我认知记录能合并成一条更稳定的协作原则。",
        },
    ]

    candidates: list[dict[str, Any]] = []
    for theme in theme_definitions:
        rows = find_rows_by_keywords(eligible_rows, theme["keywords"])
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=lambda item: (-item.importance, item.id))[:8]
        candidates.append(
            {
                "category": theme["category"],
                "title": theme["title"],
                "rows": rows,
                "draft": theme["draft"],
                "reason": theme["reason"],
                "source_action": "默认保留原子记忆；压缩总结只作为上层索引。只有纯重复、低信息密度、且没有可复用细节的阶段性记录，才可以在用户确认后考虑归档。",
            }
        )

    candidates.sort(key=lambda item: (-len(item["rows"]), item["category"], item["title"]))
    return candidates[:10]


def append_temporary_memory_review(lines: list[str], memories: list[MemoryRow], end_at: datetime) -> None:
    true_todos = [
        row
        for row in memories
        if row.category == "临时待办" or (looks_temporary(row) and not looks_memory_lifecycle_design(row))
    ]
    lifecycle_design = [
        row
        for row in memories
        if row.category != "临时待办" and looks_temporary(row) and looks_memory_lifecycle_design(row)
    ]
    if not true_todos and not lifecycle_design:
        lines.append("- 暂无明显短期记忆候选。")
        return

    if true_todos:
        lines.extend(["### 真正临时待办", ""])
    for row in sorted(true_todos, key=lambda item: (parse_dt(item.created_at), item.id)):
        status = temporary_status(row, end_at)
        lines.extend(
            [
                f"- memory {row.id} / raw {row.raw_message_id} / {row.category}: {row.title or short(row.content, 40)}",
                f"  - 状态判断：{status}",
                "  - 建议：第一版只观察，不自动归档；如用户确认已完成或已被长期总结吸收，再手动 archive。",
            ]
        )

    if lifecycle_design:
        lines.extend(["", "### 时间/短期机制设计（不当作过期待办）", ""])
    for row in sorted(lifecycle_design, key=lambda item: (-item.importance, item.id)):
        lines.extend(
            [
                f"- memory {row.id} / raw {row.raw_message_id} / {row.category}: {row.title or short(row.content, 40)}",
                "  - 状态判断：这是小柴机制设计，不是用户当天必须完成的待办。",
                "  - 建议：保留为产品改进证据；等周度压缩总结确认后，再判断是否被长期总结吸收。",
            ]
        )


def looks_temporary(row: MemoryRow) -> bool:
    text = f"{row.title}\n{row.content}\n{row.raw_content}"
    return any(term in text for term in ("今天", "明天", "后天", "下周", "待办", "别忘", "面试前", "出发前", "截止"))


def looks_memory_lifecycle_design(row: MemoryRow) -> bool:
    text = f"{row.title}\n{row.content}\n{row.raw_content}"
    return any(
        term in text
        for term in (
            "机制",
            "提醒",
            "归档",
            "压缩",
            "衰减",
            "生命周期",
            "短期记忆",
            "过期",
            "删除",
            "周报",
            "Memory Compression",
            "日报",
            "召回",
            "检索",
        )
    )


def temporary_status(row: MemoryRow, end_at: datetime) -> str:
    text = f"{row.title}\n{row.content}\n{row.raw_content}"
    created_date = parse_dt(row.created_at).date()
    if "明天" in text and created_date < end_at.date():
        return "可能已过期：原文含“明天”，创建日期早于窗口结束日"
    if "今天" in text and created_date < end_at.date():
        return "可能已过期：原文含“今天”，但已跨日"
    if any(term in text for term in ("下周", "周一", "周二", "周三", "周四", "周五", "周六", "周日")):
        return "有时间边界：需要用户确认是否完成或仍有效"
    return "短期/阶段性：需要用户确认是否仍有效"


def append_do_not_compress(lines: list[str], by_category: dict[str, list[MemoryRow]]) -> None:
    notes: list[str] = []
    for category, rows in sorted(by_category.items()):
        if category == "未来产品设想":
            notes.append(f"- `{category}` 有 {len(rows)} 条：第一版只做方向观察，不压成路线图，避免过早固化未来产品。")
        elif len(rows) == 1:
            row = rows[0]
            notes.append(f"- `{category}` 只有 1 条（memory {row.id}）：证据不足，暂不压缩。")
        elif category in {"信息安全", "生活感悟", "其他"} and len(rows) <= 4:
            notes.append(f"- `{category}` 有 {len(rows)} 条：先保留为原子记忆，不急着压缩，避免把低密度内容写成空泛总结。")
    if not notes:
        lines.append("- 暂无。")
        return
    lines.extend(notes)


def append_confirmation_questions(lines: list[str], memories: list[MemoryRow], raw_ignored: list[dict[str, Any]]) -> None:
    questions = [
        "1. 本报告提取出的长期价值，哪些准确、哪些只是阶段性材料？",
        "2. 真正临时待办里，哪些已经完成、过期或仍需要保留？",
        "3. 时间/短期机制设计里，哪些可以提取成长期规则，哪些只保留为证据？",
    ]
    if raw_ignored:
        questions.append("4. 被忽略的短概念/碎片里，哪些其实值得作为 `学习` 记录保存？")
    if any(row.category == "未来产品设想" for row in memories):
        questions.append("5. 未来产品设想是否只保留方向信号，暂不压成明确路线图？")
    lines.extend(questions)


def append_ignored_raw(lines: list[str], raw_ignored: list[dict[str, Any]]) -> None:
    if not raw_ignored:
        lines.append("- none")
        return
    worth_reviewing = [row for row in raw_ignored if maybe_concept_note(str(row["content"]))]
    low_signal = [row for row in raw_ignored if row not in worth_reviewing]
    if worth_reviewing:
        lines.extend(["### 可能值得转成学习/技术记录", ""])
        for row in worth_reviewing:
            lines.append(f"- raw {row['id']} / {row['created_at']}: {short(str(row['content']), 120)}")
    if low_signal:
        lines.extend(["", "### 低信号或待判断", ""])
        for row in low_signal:
            lines.append(f"- raw {row['id']} / {row['created_at']}: {short(str(row['content']), 120)}")


def find_rows_by_keywords(rows: list[MemoryRow], keywords: tuple[str, ...]) -> list[MemoryRow]:
    matched: list[MemoryRow] = []
    lowered_keywords = tuple(keyword.lower() for keyword in keywords)
    for row in rows:
        text = "\n".join([row.title, row.content, row.category, " ".join(row.topics)]).lower()
        if any(keyword in text for keyword in lowered_keywords):
            matched.append(row)
    return matched


def maybe_concept_note(text: str) -> bool:
    return any(term in text for term in ("就是", "区别", "类似", "概念", "定义", "RAG", "memory", "recall", "workflow", "agent"))


def parse_dt(value: str) -> datetime:
    return datetime.strptime(value[:19], "%Y-%m-%d %H:%M:%S")


def fmt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def short(text: str, limit: int) -> str:
    clean = " ".join(str(text).split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1] + "..."


def fenced(text: str) -> str:
    fence = "```"
    if fence in text:
        fence = "````"
    return f"{fence}\n{text}\n{fence}"


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
