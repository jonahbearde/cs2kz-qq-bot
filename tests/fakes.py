"""决策核心测试缝的注入替身：fake clock + fake sender。

按 spec 的 Testing Decisions：所有自动化测试只打决策核心这一个缝，
断言外部可观察行为（什么时刻发了什么内容），不断言内部结构。
Tip List 与 Rotation 状态用真实临时文件（pytest tmp_path）。

FakeClock 的 sleep 直接推进虚拟时间；可用 at() 在睡眠途中安排事件
（改贴士文件、损坏状态文件、时钟跳变），用 stop_at 结束仿真。
SimulationEnd 继承 BaseException，确保不被核心的 except Exception 吞掉。
"""

from __future__ import annotations

import asyncio
import heapq
from datetime import datetime, timedelta
from typing import Callable

from tipbot.core import BEIJING, DecisionCore  # 时区常量与缝类型直接复用，不重复定义


def at(year: int, month: int, day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    """构造北京时间（UTC+8）的 aware datetime。"""
    return datetime(year, month, day, hour, minute, second, tzinfo=BEIJING)


class SimulationEnd(BaseException):
    """虚拟时间到达 stop_at：结束核心 run() 循环，仅供测试使用。"""


class FakeClock:
    """注入时钟：now() 读虚拟时间，sleep() 推进虚拟时间。"""

    def __init__(self, start: datetime, stop_at: datetime | None = None) -> None:
        self._now = start
        self._stop_at = stop_at
        self._events: list[tuple[datetime, int, Callable[[], None]]] = []
        self._seq = 0

    def now(self) -> datetime:
        return self._now

    def at(self, moment: datetime, fn: Callable[[], None]) -> None:
        """在虚拟时刻 moment 执行 fn（sleep 经过该时刻时触发）。"""
        heapq.heappush(self._events, (moment, self._seq, fn))
        self._seq += 1

    def jump_to(self, moment: datetime) -> None:
        """时钟跳变（模拟系统休眠/宕机后的时间流逝）。"""
        self._now = moment

    async def sleep(self, seconds: float) -> None:
        target = self._now + timedelta(seconds=seconds)
        while self._events and self._events[0][0] <= target:
            moment, _, fn = heapq.heappop(self._events)
            self._now = moment
            fn()
            self._check_stop()
        self._now = max(self._now, target)  # 事件可能已把时钟跳到 target 之后（模拟休眠）
        self._check_stop()

    def _check_stop(self) -> None:
        if self._stop_at is not None and self._now >= self._stop_at:
            raise SimulationEnd


class SendError(RuntimeError):
    """fake sender 的发送失败。"""


class FakeSender:
    """注入发送器：记录每次尝试与成功发送的（时刻, Tip）。

    fail_next：接下来 N 次尝试失败（无论内容）。
    fail_tips：{Tip: 剩余失败次数}，按内容注入失败。
    """

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock
        self.sent: list[tuple[datetime, str]] = []
        self.attempts: list[tuple[datetime, str, bool]] = []
        self.fail_next = 0
        self.fail_tips: dict[str, int] = {}

    async def send(self, tip: str) -> None:
        fail = self.fail_next > 0 or self.fail_tips.get(tip, 0) > 0
        if fail:
            if self.fail_next > 0:
                self.fail_next -= 1
            else:
                self.fail_tips[tip] -= 1
            self.attempts.append((self._clock.now(), tip, False))
            raise SendError(f"模拟发送失败：{tip}")
        self.attempts.append((self._clock.now(), tip, True))
        self.sent.append((self._clock.now(), tip))


def run_core(core: DecisionCore) -> None:
    """驱动核心 run() 直到 FakeClock 抛出 SimulationEnd。"""

    async def _go() -> None:
        try:
            await core.run()
        except SimulationEnd:
            pass

    asyncio.run(_go())