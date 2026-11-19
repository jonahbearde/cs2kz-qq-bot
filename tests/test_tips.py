"""Tip List 加载的行为测试。

测试缝：tipbot.tips.load_tips(path) —— 决策核心的 Tip List 输入侧。
按 spec 的 Testing Decisions：真实临时文件，断言外部可观察行为。
QQ 适配层（botpy 接线、.env 装载、@ 捕获）不做单元测试，按手册人工验收。
"""

from __future__ import annotations

from pathlib import Path

from tipbot.tips import load_tips


def test_one_tip_per_line_in_file_order(tmp_path: Path) -> None:
    tips_file = tmp_path / "tips.txt"
    tips_file.write_text("第一条贴士\n第二条贴士\n", encoding="utf-8")

    assert load_tips(tips_file) == ["第一条贴士", "第二条贴士"]


def test_blank_lines_are_ignored(tmp_path: Path) -> None:
    tips_file = tmp_path / "tips.txt"
    tips_file.write_text("第一条贴士\n\n   \n第二条贴士\n\n", encoding="utf-8")

    assert load_tips(tips_file) == ["第一条贴士", "第二条贴士"]


def test_tip_whitespace_is_stripped(tmp_path: Path) -> None:
    tips_file = tmp_path / "tips.txt"
    tips_file.write_text("  第一条贴士  \n\t第二条贴士\t\n", encoding="utf-8")

    assert load_tips(tips_file) == ["第一条贴士", "第二条贴士"]


def test_comment_lines_are_ignored(tmp_path: Path) -> None:
    tips_file = tmp_path / "tips.txt"
    tips_file.write_text(
        "# 头部注释\n第一条贴士\n  # 缩进的注释\n第二条贴士\n",
        encoding="utf-8",
    )

    assert load_tips(tips_file) == ["第一条贴士", "第二条贴士"]


def test_missing_file_yields_empty_list(tmp_path: Path) -> None:
    assert load_tips(tmp_path / "不存在的文件.txt") == []


def test_empty_file_yields_empty_list(tmp_path: Path) -> None:
    tips_file = tmp_path / "tips.txt"
    tips_file.write_text("", encoding="utf-8")

    assert load_tips(tips_file) == []


def test_utf8_bom_does_not_leak_into_first_tip(tmp_path: Path) -> None:
    # Windows 记事本可能保存为带 BOM 的 UTF-8
    tips_file = tmp_path / "tips.txt"
    tips_file.write_bytes("\ufeff第一条贴士\n第二条贴士\n".encode("utf-8"))

    assert load_tips(tips_file) == ["第一条贴士", "第二条贴士"]


def test_shipped_sample_tip_list_has_3_to_5_marked_examples() -> None:
    # 验收标准：示例 Tip List 含 3–5 条明确标注为示例的条目
    sample = Path(__file__).resolve().parent.parent / "tips.txt"

    tips = load_tips(sample)

    assert 3 <= len(tips) <= 5
    assert all("示例" in tip for tip in tips)
