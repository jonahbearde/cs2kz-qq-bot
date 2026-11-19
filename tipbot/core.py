"""决策核心：给定当前时刻、Tip List、Rotation 状态与配置，决定是否发送、发送哪条。

与 QQ 适配层隔离：时钟与发送动作经 Protocol 注入（生产用真实时钟与 botpy，
测试用 fake clock + fake sender），Tip List 与 Rotation 状态走真实文件。
时区固定北京时间（Asia/Shanghai，全年 UTC+8、无夏令时，用固定偏移即可，
不依赖系统 tz 数据库），与服务器时区无关。
"""

from __future__ import annotations

import json
import logging
import math
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from tipbot.tips import load_tips

_log = logging.getLogger("tipbot.core")

# Asia/Shanghai 自 1991 年起全年 UTC+8、无夏令时；固定偏移免 tzdata 依赖（Windows/3.8 可用）。
BEIJING = timezone(timedelta(hours=8))

RETRY_DELAY_SECONDS = 30


@dataclass(frozen=True)
class Schedule:
    """Send Window 与发送间隔。时刻对齐墙钟的间隔边界（自当日 00:00 起算）。

    窗口为当日 [start, end) 分钟区间，end=1440 表示 24:00（不含）。
    """

    interval_minutes: int = 30
    window_start_minute: int = 9 * 60
    window_end_minute: int = 24 * 60

    def __post_init__(self) -> None:
        if self.interval_minutes < 1:
            raise ValueError("发送间隔必须 ≥ 1 分钟")
        if not (0 <= self.window_start_minute < self.window_end_minute <= 24 * 60):
            raise ValueError("Send Window 须满足 00:00 ≤ 起 < 止 ≤ 24:00")
        interval = self.interval_minutes * 60
        start = self.window_start_minute * 60
        end = self.window_end_minute * 60
        if math.ceil(start / interval) * interval >= end:
            raise ValueError("Send Window 内不存在任何对齐时刻：请加大窗口或缩小间隔")

    def next_moment(self, floor: datetime) -> datetime:
        """≥ floor 的首个窗口内对齐时刻（跨天则滚到次日窗口）。floor 须为北京时间。"""
        interval = self.interval_minutes * 60
        start = self.window_start_minute * 60
        end = self.window_end_minute * 60
        midnight = floor.replace(hour=0, minute=0, second=0, microsecond=0)
        while True:
            offset = (floor - midnight).total_seconds()
            k = math.ceil(offset / interval)
            if k * interval < start:
                k = math.ceil(start / interval)
            if k * interval < end:
                return midnight + timedelta(seconds=k * interval)
            midnight += timedelta(days=1)
            floor = midnight


class Clock(Protocol):
    def now(self) -> datetime: ...

    async def sleep(self, seconds: float) -> None: ...


class Sender(Protocol):
    async def send(self, tip: str) -> None:
        """发送一条纯文本 Tip；失败抛异常。"""
        ...


class DecisionCore:
    """调度 + Rotation 生命周期：窗口内按对齐时刻逐条发送，错过不补发。"""

    def __init__(
        self,
        *,
        clock: Clock,
        sender: Sender,
        tips_file: Path,
        state_file: Path,
        schedule: Schedule | None = None,
    ) -> None:
        self._clock = clock
        self._sender = sender
        self._tips_file = tips_file
        self._state_file = state_file
        self._schedule = schedule if schedule is not None else Schedule()
        self._rng = random.Random()
        self._tips: list[str] = []
        self._tips_signature: tuple[int, int] | None = None
        self._order: list[str] = []
        self._cursor = 0

    async def run(self) -> None:
        self._bootstrap()
        last_processed: datetime | None = None
        while True:
            now = self._clock.now().astimezone(BEIJING)
            floor = now
            if last_processed is not None and last_processed >= now:
                floor = last_processed + timedelta(microseconds=1)
            target = self._schedule.next_moment(floor)
            delay = (target - now).total_seconds()
            if delay > 0:
                await self._clock.sleep(delay)
                now = self._clock.now().astimezone(BEIJING)
                if now >= target + timedelta(minutes=self._schedule.interval_minutes):
                    continue  # 一觉睡过整个间隔（如系统休眠）：错过的不补发
            last_processed = target
            try:
                await self._process_moment()
            except Exception:
                # 韧性：单个时刻的意外异常不终止进程，等下一对齐时刻
                _log.exception("处理时刻 %s 时发生意外异常，跳过该时刻", target.isoformat())

    def _bootstrap(self) -> None:
        """启动：读 Tip List 与 Rotation 状态；状态与当前列表一致则续发，否则重新洗牌。"""
        self._tips_signature = self._stat_signature()
        self._tips = load_tips(self._tips_file)
        state = self._read_state()
        if state is not None and state["tips"] == self._tips:
            self._order = state["order"]
            self._cursor = state["cursor"]
            _log.info("恢复 Rotation：本轮已发 %d/%d 条", self._cursor, len(self._order))
        else:
            self._reshuffle("启动新 Rotation")

    def _read_state(self) -> dict | None:
        """读并验证 Rotation 状态；缺失静默返回 None，损坏记警告后返回 None（重建）。"""
        try:
            raw = self._state_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            _log.warning("Rotation 状态文件不可读（%s），重建。", self._state_file)
            return None
        try:
            data = json.loads(raw)
        except ValueError:
            data = None
        if (
            isinstance(data, dict)
            and isinstance(data.get("tips"), list)
            and all(isinstance(t, str) for t in data["tips"])
            and isinstance(data.get("order"), list)
            and all(isinstance(t, str) for t in data["order"])
            and isinstance(data.get("cursor"), int)
            and not isinstance(data["cursor"], bool)
            and 0 <= data["cursor"] <= len(data["order"])
            and Counter(data["order"]) == Counter(data["tips"])
        ):
            return data
        _log.warning("Rotation 状态文件损坏（%s），重建。", self._state_file)
        return None

    def _stat_signature(self) -> tuple[int, int] | None:
        """文件修改时间+大小；缺失/不可读为 None。每个调度时刻检测，变化即热加载。"""
        try:
            st = self._tips_file.stat()
        except OSError:
            return None
        return (st.st_mtime_ns, st.st_size)

    def _reload_tips_if_changed(self) -> None:
        signature = self._stat_signature()
        if signature == self._tips_signature:
            return
        self._tips_signature = signature
        tips = load_tips(self._tips_file)
        if tips == self._tips:
            return  # 仅 mtime 变化（如 touch）：内容未增删改，不重新洗牌
        self._tips = tips
        self._reshuffle("Tip List 已变更（热加载）")

    def _reshuffle(self, reason: str) -> None:
        self._order = list(self._tips)
        self._rng.shuffle(self._order)
        self._cursor = 0
        _log.info("%s：重新洗牌（%d 条）", reason, len(self._order))

    def _save_state(self) -> None:
        payload = {"tips": self._tips, "order": self._order, "cursor": self._cursor}
        tmp = self._state_file.with_name(self._state_file.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._state_file)

    async def _process_moment(self) -> None:
        self._reload_tips_if_changed()
        if not self._tips:
            _log.warning(
                "Tip List 为空或文件缺失（%s），本时刻跳过发送；机器人继续运行。",
                self._tips_file,
            )
            return
        if self._cursor >= len(self._order):
            self._reshuffle("一轮发完")
        tip = self._order[self._cursor]
        self._cursor += 1
        try:
            await self._sender.send(tip)
        except Exception:
            _log.exception("发送 Tip 失败，%d 秒后重试一次：%s", RETRY_DELAY_SECONDS, tip)
            await self._clock.sleep(RETRY_DELAY_SECONDS)
            try:
                await self._sender.send(tip)
            except Exception:
                _log.exception("重试仍失败，跳过该 Tip，等待下一时刻：%s", tip)
            else:
                _log.info("重试成功，已发送 Tip：%s", tip)
        else:
            _log.info("已发送 Tip：%s", tip)
        self._save_state()  # 无论成败，游标已前进（失败条被跳过）；重启不重发