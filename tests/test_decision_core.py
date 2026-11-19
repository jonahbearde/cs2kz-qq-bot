"""决策核心的行为测试（spec 单一测试缝）。

缝：DecisionCore(clock=fake, sender=fake, tips_file/state_file=真实临时文件)。
只断言外部可观察行为：什么时刻发了什么内容、记了什么警告/错误。
QQ 适配层（botpy 接线、.env 装载、@ 捕获）不做单元测试，按手册人工验收。
"""

from __future__ import annotations

import logging
from datetime import timedelta, timezone
from pathlib import Path

import pytest

from fakes import BEIJING, FakeClock, FakeSender, at, run_core

from tipbot.core import DecisionCore, Schedule


def make_core(
    tmp_path: Path,
    clock: FakeClock,
    sender: FakeSender,
    tips: list[str] | None = None,
    schedule: Schedule | None = None,
) -> DecisionCore:
    tips_file = tmp_path / "tips.txt"
    if tips is not None:
        tips_file.write_text("\n".join(tips) + "\n", encoding="utf-8")
    return DecisionCore(
        clock=clock,
        sender=sender,
        tips_file=tips_file,
        state_file=tmp_path / "rotation_state.json",
        schedule=schedule,
    )


def test_silent_before_window_first_tip_at_nine(tmp_path: Path) -> None:
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 9, 1))
    sender = FakeSender(clock)
    core = make_core(tmp_path, clock, sender, tips=["贴士一", "贴士二"])

    run_core(core)

    assert len(sender.sent) == 1
    assert sender.sent[0][0] == at(2026, 11, 19, 9, 0)
    assert sender.sent[0][1] in ("贴士一", "贴士二")


def test_full_day_thirty_tips_on_the_half_hour_silent_at_midnight(tmp_path: Path) -> None:
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 20, 9, 1))
    sender = FakeSender(clock)
    core = make_core(tmp_path, clock, sender, tips=["唯一贴士"])

    run_core(core)

    expected = [at(2026, 11, 19, 9, 0) + timedelta(minutes=30 * i) for i in range(30)]
    assert [moment for moment, _ in sender.sent[:30]] == expected  # 09:00…23:30，24:00 起沉默
    assert sender.sent[29][0] == at(2026, 11, 19, 23, 30)
    assert sender.sent[30] == (at(2026, 11, 20, 9, 0), "唯一贴士")  # 次日首条仍是 09:00
    assert len(sender.sent) == 31


def test_mid_window_start_waits_for_next_aligned_moment(tmp_path: Path) -> None:
    clock = FakeClock(start=at(2026, 11, 19, 9, 10), stop_at=at(2026, 11, 19, 9, 31))
    sender = FakeSender(clock)
    core = make_core(tmp_path, clock, sender, tips=["贴士一"])

    run_core(core)

    assert sender.sent == [(at(2026, 11, 19, 9, 30), "贴士一")]  # 不立即发


def test_start_exactly_on_boundary_sends_at_that_boundary(tmp_path: Path) -> None:
    clock = FakeClock(start=at(2026, 11, 19, 9, 0), stop_at=at(2026, 11, 19, 9, 1))
    sender = FakeSender(clock)
    core = make_core(tmp_path, clock, sender, tips=["贴士一"])

    run_core(core)

    assert sender.sent == [(at(2026, 11, 19, 9, 0), "贴士一")]


def test_late_night_start_silent_until_next_morning(tmp_path: Path) -> None:
    clock = FakeClock(start=at(2026, 11, 19, 23, 45), stop_at=at(2026, 11, 20, 9, 1))
    sender = FakeSender(clock)
    core = make_core(tmp_path, clock, sender, tips=["贴士一"])

    run_core(core)

    assert sender.sent == [(at(2026, 11, 20, 9, 0), "贴士一")]


def test_window_follows_beijing_time_regardless_of_clock_timezone(tmp_path: Path) -> None:
    # 同一时刻用 UTC 与纽约时间表达：01:00 UTC = 09:00 北京 = 前一日 20:00 纽约（EST）
    utc = timezone.utc
    new_york = timezone(timedelta(hours=-5))
    for tz in (utc, new_york):
        start = at(2026, 11, 19, 9, 0).astimezone(tz)
        clock = FakeClock(start=start - timedelta(hours=1), stop_at=start + timedelta(minutes=1))
        sender = FakeSender(clock)
        core = make_core(tmp_path, clock, sender, tips=["贴士一"])

        run_core(core)

        assert len(sender.sent) == 1
        assert sender.sent[0][0].astimezone(BEIJING) == at(2026, 11, 19, 9, 0)


def test_interval_and_window_are_configurable(tmp_path: Path) -> None:
    clock = FakeClock(start=at(2026, 11, 19, 9, 30), stop_at=at(2026, 11, 20, 10, 1))
    sender = FakeSender(clock)
    schedule = Schedule(interval_minutes=15, window_start_minute=10 * 60, window_end_minute=11 * 60)
    core = make_core(tmp_path, clock, sender, tips=["贴士一"], schedule=schedule)

    run_core(core)

    assert [m for m, _ in sender.sent] == [
        at(2026, 11, 19, 10, 0),
        at(2026, 11, 19, 10, 15),
        at(2026, 11, 19, 10, 30),
        at(2026, 11, 19, 10, 45),
        at(2026, 11, 20, 10, 0),
    ]


def test_alignment_uses_interval_boundaries_from_midnight(tmp_path: Path) -> None:
    # 45 分钟间隔：自 00:00 起的边界为 :00/:45/次小时 :30…，而非启动时刻起算
    clock = FakeClock(start=at(2026, 11, 19, 8, 50), stop_at=at(2026, 11, 19, 10, 31))
    sender = FakeSender(clock)
    core = make_core(
        tmp_path, clock, sender, tips=["贴士一"], schedule=Schedule(interval_minutes=45)
    )

    run_core(core)

    assert [m for m, _ in sender.sent] == [
        at(2026, 11, 19, 9, 0),
        at(2026, 11, 19, 9, 45),
        at(2026, 11, 19, 10, 30),
    ]


def test_rotation_covers_all_tips_without_repeats_within_round(tmp_path: Path) -> None:
    tips = [f"贴士{i}" for i in range(5)]
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 13, 31))
    sender = FakeSender(clock)
    core = make_core(tmp_path, clock, sender, tips=tips)

    run_core(core)

    assert len(sender.sent) == 10  # 09:00…13:30 共 10 个时刻，两轮
    for round_start in (0, 5):
        round_tips = [tip for _, tip in sender.sent[round_start : round_start + 5]]
        assert sorted(round_tips) == sorted(tips)  # 全覆盖且无重复


def test_bag_is_shuffled_and_reshuffled_each_round(tmp_path: Path) -> None:
    tips = [f"贴士{i}" for i in range(5)]
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 20, 13, 31))
    sender = FakeSender(clock)
    core = make_core(tmp_path, clock, sender, tips=tips)

    run_core(core)

    rounds = [
        tuple(tip for _, tip in sender.sent[i : i + 5])
        for i in range(0, len(sender.sent) - len(sender.sent) % 5, 5)
    ]
    assert len(rounds) >= 8
    assert any(r != tuple(tips) for r in rounds)  # 洗牌：不是文件顺序照发
    assert len(set(rounds)) > 1  # 发完重新洗牌：各轮顺序不全相同


def test_restart_resumes_rotation_without_repeats(tmp_path: Path) -> None:
    tips = [f"贴士{i}" for i in range(5)]
    clock_a = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 10, 1))
    sender_a = FakeSender(clock_a)
    core_a = make_core(tmp_path, clock_a, sender_a, tips=tips)
    run_core(core_a)
    assert len(sender_a.sent) == 3  # 09:00/09:30/10:00
    assert (tmp_path / "rotation_state.json").is_file()  # 顺序+游标已持久化

    # 重启（新进程、新时钟），窗口中途启动：等到 10:30 续发，不从头再来
    clock_b = FakeClock(start=at(2026, 11, 19, 10, 10), stop_at=at(2026, 11, 19, 11, 31))
    sender_b = FakeSender(clock_b)
    core_b = make_core(tmp_path, clock_b, sender_b, tips=tips)
    run_core(core_b)

    assert [m for m, _ in sender_b.sent] == [
        at(2026, 11, 19, 10, 30),
        at(2026, 11, 19, 11, 0),
        at(2026, 11, 19, 11, 30),
    ]
    combined = [tip for _, tip in sender_a.sent + sender_b.sent]
    assert sorted(combined[:5]) == sorted(tips)  # 跨重启一轮内全覆盖且无重复


@pytest.mark.parametrize(
    "garbage",
    [
        b"\xff\xfe not json at all",
        b"[]",
        b'{"tips": "not-a-list", "order": [], "cursor": 0}',
        b'{"tips": ["a"], "order": ["a", 1], "cursor": 0}',
        b'{"tips": ["a"], "order": ["a"], "cursor": 5}',
        b'{"tips": ["a"], "order": ["a"], "cursor": -1}',
        b'{"tips": ["a"], "order": ["b"], "cursor": 0}',
        b'{"tips": ["a"], "order": ["a"], "cursor": true}',
        b'{"order": ["a"], "cursor": 0}',
    ],
)
def test_corrupt_state_file_rebuilds_cleanly(tmp_path: Path, caplog, garbage: bytes) -> None:
    tips = [f"贴士{i}" for i in range(5)]
    tips_file = tmp_path / "tips.txt"
    tips_file.write_text("\n".join(tips) + "\n", encoding="utf-8")
    state_file = tmp_path / "rotation_state.json"
    state_file.write_bytes(garbage)
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 11, 1))
    sender = FakeSender(clock)
    core = DecisionCore(
        clock=clock, sender=sender, tips_file=tips_file, state_file=state_file
    )

    with caplog.at_level(logging.WARNING, logger="tipbot.core"):
        run_core(core)

    assert "状态" in caplog.text and "重建" in caplog.text
    assert len(sender.sent) == 5
    assert sorted(tip for _, tip in sender.sent) == sorted(tips)  # 干净重建后正常轮播


def test_hot_reload_add_delete_reshuffles_and_deleted_tip_never_returns(tmp_path: Path) -> None:
    tips_file = tmp_path / "tips.txt"
    tips_file.write_text("甲\n乙\n丙\n", encoding="utf-8")
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 10, 31))
    clock.at(at(2026, 11, 19, 9, 10), lambda: tips_file.write_text("甲\n乙\n丁\n", encoding="utf-8"))
    sender = FakeSender(clock)
    core = DecisionCore(
        clock=clock, sender=sender, tips_file=tips_file, state_file=tmp_path / "rotation_state.json"
    )

    run_core(core)

    assert [m for m, _ in sender.sent] == [
        at(2026, 11, 19, 9, 0),
        at(2026, 11, 19, 9, 30),
        at(2026, 11, 19, 10, 0),
        at(2026, 11, 19, 10, 30),
    ]
    after_change = [tip for _, tip in sender.sent[1:]]
    assert sorted(after_change) == sorted(["甲", "乙", "丁"])  # 增删后重新洗牌，新列表全覆盖
    assert "丙" not in after_change  # 被删除的 Tip 不再出现
    assert "丁" in after_change  # 新增的 Tip 立即进入轮播


def test_hot_reload_edit_replaces_content_without_restart(tmp_path: Path) -> None:
    tips_file = tmp_path / "tips.txt"
    tips_file.write_text("甲\n乙\n丙\n", encoding="utf-8")
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 10, 31))
    clock.at(
        at(2026, 11, 19, 9, 10),
        lambda: tips_file.write_text("甲\n乙\n丙改\n", encoding="utf-8"),
    )
    sender = FakeSender(clock)
    core = DecisionCore(
        clock=clock, sender=sender, tips_file=tips_file, state_file=tmp_path / "rotation_state.json"
    )

    run_core(core)

    after_change = [tip for _, tip in sender.sent[1:]]
    assert sorted(after_change) == sorted(["甲", "乙", "丙改"])
    assert "丙" not in after_change


def test_empty_or_missing_list_skips_with_warning_and_keeps_running(
    tmp_path: Path, caplog
) -> None:
    tips_file = tmp_path / "tips.txt"  # 启动时缺失
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 11, 31))
    clock.at(at(2026, 11, 19, 9, 40), lambda: tips_file.write_text("甲\n乙\n", encoding="utf-8"))
    clock.at(at(2026, 11, 19, 10, 10), lambda: tips_file.write_text("", encoding="utf-8"))
    clock.at(
        at(2026, 11, 19, 10, 40), lambda: tips_file.write_text("甲\n乙\n丙\n", encoding="utf-8")
    )
    sender = FakeSender(clock)
    core = DecisionCore(
        clock=clock, sender=sender, tips_file=tips_file, state_file=tmp_path / "rotation_state.json"
    )

    with caplog.at_level(logging.WARNING, logger="tipbot.core"):
        run_core(core)

    assert [m for m, _ in sender.sent] == [
        at(2026, 11, 19, 10, 0),
        at(2026, 11, 19, 11, 0),
        at(2026, 11, 19, 11, 30),
    ]
    assert caplog.text.count("为空或文件缺失") == 3  # 09:00/09:30 缺失，10:30 为空


def test_transient_failure_retries_once_thirty_seconds_later(tmp_path: Path) -> None:
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 9, 31))
    sender = FakeSender(clock)
    sender.fail_next = 1  # 首次尝试失败，重试成功
    core = make_core(tmp_path, clock, sender, tips=["贴士一", "贴士二"])

    run_core(core)

    assert len(sender.attempts) == 3
    assert sender.attempts[0] == (at(2026, 11, 19, 9, 0), sender.attempts[0][1], False)
    assert sender.attempts[1] == (at(2026, 11, 19, 9, 0, 30), sender.attempts[0][1], True)
    assert sender.sent[0][0] == at(2026, 11, 19, 9, 0, 30)  # 重试成功即发送
    assert sender.sent[1][0] == at(2026, 11, 19, 9, 30)  # 下一时刻照常
    assert sender.sent[1][1] != sender.sent[0][1]  # 游标已前进


def test_persistent_failure_skips_tip_and_waits_for_next_moment(tmp_path: Path, caplog) -> None:
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 9, 31))
    sender = FakeSender(clock)
    sender.fail_next = 2  # 首条两次尝试均失败
    core = make_core(tmp_path, clock, sender, tips=["贴士一", "贴士二"])

    with caplog.at_level(logging.ERROR, logger="tipbot.core"):
        run_core(core)

    failed_tip = sender.attempts[0][1]
    assert sender.attempts[:2] == [
        (at(2026, 11, 19, 9, 0), failed_tip, False),
        (at(2026, 11, 19, 9, 0, 30), failed_tip, False),
    ]
    assert len(sender.sent) == 1
    assert sender.sent[0][0] == at(2026, 11, 19, 9, 30)  # 跳过失败条，等下一时刻
    assert sender.sent[0][1] != failed_tip
    assert len(caplog.records) >= 2  # 两次失败均入日志


def test_restart_after_downtime_does_not_backfill_missed_moments(tmp_path: Path) -> None:
    tips = [f"贴士{i}" for i in range(5)]
    clock_a = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 9, 31))
    sender_a = FakeSender(clock_a)
    run_core(make_core(tmp_path, clock_a, sender_a, tips=tips))
    assert len(sender_a.sent) == 2  # 09:00/09:30 后宕机

    # 15:00 恢复：错过 10:00–14:30 共 10 个时刻，不补发
    clock_b = FakeClock(start=at(2026, 11, 19, 15, 0), stop_at=at(2026, 11, 19, 15, 31))
    sender_b = FakeSender(clock_b)
    run_core(make_core(tmp_path, clock_b, sender_b, tips=tips))

    assert [m for m, _ in sender_b.sent] == [at(2026, 11, 19, 15, 0), at(2026, 11, 19, 15, 30)]


def test_clock_jump_mid_run_skips_stale_moment_without_burst(tmp_path: Path) -> None:
    clock = FakeClock(start=at(2026, 11, 19, 8, 0), stop_at=at(2026, 11, 19, 15, 31))
    clock.at(at(2026, 11, 19, 9, 5), lambda: clock.jump_to(at(2026, 11, 19, 15, 0)))
    sender = FakeSender(clock)
    core = make_core(tmp_path, clock, sender, tips=["贴士一"])

    run_core(core)

    assert [m for m, _ in sender.sent] == [
        at(2026, 11, 19, 9, 0),
        at(2026, 11, 19, 15, 0),
        at(2026, 11, 19, 15, 30),
    ]  # 无 09:30–14:30 的补发突发


@pytest.mark.parametrize(
    "kwargs",
    [
        {"interval_minutes": 0},
        {"interval_minutes": -5},
        {"window_start_minute": 600, "window_end_minute": 600},
        {"window_start_minute": 600, "window_end_minute": 540},
        {"window_end_minute": 25 * 60},
        {"window_start_minute": -1},
        {"interval_minutes": 120, "window_start_minute": 540, "window_end_minute": 600},
    ],
)
def test_invalid_schedule_is_rejected(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        Schedule(**kwargs)