"""入口：在项目根目录运行 `python -m tipbot`。"""

from __future__ import annotations

from pathlib import Path

import botpy

from tipbot.bot import TipBot
from tipbot.config import load_config

TIPS_FILE = Path("tips.txt")


def main() -> None:
    config = load_config()
    # 只订阅公域消息（群 @ 事件）；不订阅任何需要回复的场景。
    intents = botpy.Intents(public_messages=True)
    client = TipBot(intents=intents, config=config, tips_file=TIPS_FILE)
    client.run(appid=config.app_id, secret=config.app_secret)


if __name__ == "__main__":
    main()
