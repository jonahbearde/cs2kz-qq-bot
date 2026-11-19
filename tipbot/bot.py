"""QQ 适配层：botpy 接线、@ 捕获日志、曳光弹一次性发送。

保持极薄，不做单元测试（按手册人工验收）。本层只做两件事：
1. 被 @ 时把该群 group_openid 醒目记入日志——被动捕获，绝不回复、绝不自动改配置；
2. 上线后若已配置 Target Group，主动发送一条纯文本 Tip（msg_type=0、不带 msg_id）。
"""

from __future__ import annotations

from pathlib import Path

import botpy
from botpy import logging as botpy_logging
from botpy.message import GroupMessage

from tipbot.config import Config
from tipbot.tips import load_tips

_log = botpy_logging.get_logger("tipbot")

_BANNER = "=" * 62


class TipBot(botpy.Client):
    """只发贴士的机器人：对任何消息绝不回复。"""

    def __init__(self, intents: botpy.Intents, config: Config, tips_file: Path) -> None:
        super().__init__(intents=intents)
        self._target_group_openid = config.target_group_openid
        self._tips_file = tips_file
        self._tip_attempted = False

    async def on_ready(self) -> None:
        _log.info("机器人「%s」已上线（WebSocket 出站连接，无需公网 IP/域名/Webhook）", self.robot.name)
        if self._tip_attempted:
            return  # 每次进程运行只尝试发送一条（曳光弹）；断线重连不重发，失败后重启才再试
        if not self._target_group_openid:
            _log.info(
                "尚未配置 TARGET_GROUP_OPENID：请在测试群 @ 机器人，"
                "把日志里醒目显示的 group_openid 填入 .env 后重启。"
            )
            return
        await self._send_first_tip()

    async def on_group_at_message_create(self, message: GroupMessage) -> None:
        # 被动捕获：只记日志，绝不回复，绝不自动改配置。
        _log.info(
            "\n%s\n捕获到群标识 group_openid：%s\n"
            "把上面这串值填入 .env 的 TARGET_GROUP_OPENID，重启机器人即可向该群发送 Tip。\n%s",
            _BANNER,
            message.group_openid,
            _BANNER,
        )

    async def _send_first_tip(self) -> None:
        self._tip_attempted = True  # 无论成败，本次进程运行不再尝试（重试策略属后续决策核心）
        tips = load_tips(self._tips_file)
        if not tips:
            _log.warning(
                "Tip List 为空或文件缺失（%s），本次不发送；机器人保持在线。", self._tips_file
            )
            return
        tip = tips[0]
        try:
            # 不带 msg_id = 主动推送；msg_type=0 = 纯文本；内容即 Tip 本身，无前缀。
            await self.api.post_group_message(
                group_openid=self._target_group_openid,
                msg_type=0,
                content=tip,
            )
        except Exception:
            _log.exception(
                "向 Target Group 发送 Tip 失败，机器人保持在线。"
                "若错误码为 40034105：请检查群主是否已开启「机器人主动在群聊内发言」（手册第一章第 7 节）。"
            )
            return
        _log.info("已向 Target Group 主动发送第一条 Tip：%s", tip)
