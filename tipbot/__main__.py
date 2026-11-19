"""入口：在项目根目录运行 `python -m tipbot`。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import botpy

from tipbot.bot import TipBot
from tipbot.config import load_config

TIPS_FILE = Path("tips.txt")


def main() -> None:
    config = load_config()
    # botpy 1.2.1 构造时调用 asyncio.get_event_loop()；Python 3.14 移除了其隐式建环，
    # 无当前事件循环会直接抛 RuntimeError。入口显式建环并设置，兼容 Python 3.8–3.14。
    asyncio.set_event_loop(asyncio.new_event_loop())
    # 只订阅公域消息（群 @ 事件）；不订阅任何需要回复的场景。
    intents = botpy.Intents(public_messages=True)
    client = TipBot(intents=intents, config=config, tips_file=TIPS_FILE)
    client.run(appid=config.app_id, secret=config.app_secret)


if __name__ == "__main__":
    main()
