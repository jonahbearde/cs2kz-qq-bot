"""QQ 适配层：botpy 接线、@ 捕获日志、决策核心的真实时钟与发送器。

保持极薄，不做单元测试（按手册人工验收）。本层只做三件事：
1. 被 @ 时把该群 group_openid 醒目记入日志——被动捕获，绝不回复、绝不自动改配置；
2. 上线后启动决策核心（调度/轮播/热加载/重试全在 tipbot.core，经测试缝覆盖）；
3. 把核心的发送动作落到 post_group_message（msg_type=0 纯文本、不带 msg_id 即主动推送）。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import botpy
from botpy import logging as botpy_logging
from botpy.message import GroupMessage

from tipbot.config import Config
from tipbot.core import BEIJING, DecisionCore

_log = botpy_logging.get_logger("tipbot")

_BANNER = "=" * 62


class _RealClock:
    """生产时钟：北京时间（固定 UTC+8），sleep 走事件循环。"""

    def now(self) -> datetime:
        return datetime.now(BEIJING)

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class _GroupSender:
    """把一条 Tip 主动推送到 Target Group；失败抛异常由核心重试/跳过。"""

    def __init__(self, client: TipBot, group_openid: str) -> None:
        self._client = client
        self._group_openid = group_openid

    async def send(self, tip: str) -> None:
        # 不带 msg_id = 主动推送；msg_type=0 = 纯文本；内容即 Tip 本身，无前缀。
        await self._client.api.post_group_message(
            group_openid=self._group_openid,
            msg_type=0,
            content=tip,
        )


class TipBot(botpy.Client):
    """只发贴士的机器人：对任何消息绝不回复。"""

    def __init__(
        self, intents: botpy.Intents, config: Config, tips_file: Path, state_file: Path
    ) -> None:
        super().__init__(intents=intents)
        self._target_group_openid = config.target_group_openid
        self._schedule = config.schedule
        self._core = DecisionCore(
            clock=_RealClock(),
            sender=_GroupSender(self, config.target_group_openid),
            tips_file=tips_file,
            state_file=state_file,
            schedule=config.schedule,
        )
        self._core_task: asyncio.Task | None = None

    async def on_ready(self) -> None:
        _log.info("机器人「%s」已上线（WebSocket 出站连接，无需公网 IP/域名/Webhook）", self.robot.name)
        if not self._target_group_openid:
            _log.info(
                "尚未配置 TARGET_GROUP_OPENID：请在测试群 @ 机器人，"
                "把日志里醒目显示的 group_openid 填入 .env 后重启。"
            )
            return
        if self._core_task is None:
            # 每次进程运行只启动一次；断线重连不重启核心、不重发、不突发。
            self._core_task = asyncio.create_task(self._core.run())
            self._core_task.add_done_callback(self._on_core_done)
            schedule = self._schedule
            _log.info(
                "Rotation 已启动：Send Window %02d:%02d–%02d:%02d（北京时间），每 %d 分钟一条，"
                "时刻对齐间隔边界；窗口中途启动等待下一对齐时刻，错过不补发。",
                schedule.window_start_minute // 60,
                schedule.window_start_minute % 60,
                schedule.window_end_minute // 60,
                schedule.window_end_minute % 60,
                schedule.interval_minutes,
            )

    def _on_core_done(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            _log.error("决策核心意外退出，机器人保持在线但不再发送", exc_info=exc)

    async def on_group_at_message_create(self, message: GroupMessage) -> None:
        # 被动捕获：只记日志，绝不回复，绝不自动改配置。
        _log.info(
            "\n%s\n捕获到群标识 group_openid：%s\n"
            "把上面这串值填入 .env 的 TARGET_GROUP_OPENID，重启机器人即可向该群发送 Tip。\n%s",
            _BANNER,
            message.group_openid,
            _BANNER,
        )