"""配置装载：凭据、Target Group 标识与发送节奏全部来自 .env。

QQ 适配层的一部分，保持极薄，不做单元测试（按手册人工验收）。
节奏参数的合法性由决策核心的 Schedule 校验。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from tipbot.core import Schedule


@dataclass(frozen=True)
class Config:
    app_id: str
    app_secret: str
    # 空字符串 = 未配置 Target Group：机器人只捕获群标识，不发送。
    target_group_openid: str
    schedule: Schedule = Schedule()


def _parse_window_minute(raw: str, *, allow_midnight_end: bool) -> int:
    """解析 HH:MM 为自 00:00 起的分钟数；24:00 仅允许作为窗口止。"""
    parts = raw.split(":")
    if len(parts) != 2:
        raise ValueError(f"时刻 {raw!r} 应为 HH:MM 格式")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= minute < 60) or not (0 <= hour <= 24):
        raise ValueError(f"时刻 {raw!r} 超出范围")
    if hour == 24 and not (allow_midnight_end and minute == 0):
        raise ValueError(f"时刻 {raw!r} 超出范围（24:00 只能作为窗口止）")
    return hour * 60 + minute


def load_config() -> Config:
    """从项目根目录的 .env（及环境变量）读取配置；缺少凭据时给出明确指引并退出。"""
    load_dotenv()
    app_id = os.environ.get("QQ_APP_ID", "").strip()
    app_secret = os.environ.get("QQ_APP_SECRET", "").strip()
    target_group_openid = os.environ.get("TARGET_GROUP_OPENID", "").strip()

    missing = [
        name
        for name, value in (("QQ_APP_ID", app_id), ("QQ_APP_SECRET", app_secret))
        if not value
    ]
    if missing:
        raise SystemExit(
            "缺少配置：" + "、".join(missing) + "。\n"
            "请把 .env.example 复制为 .env 并填入凭据（见手册第二章）。"
        )
    try:
        schedule = Schedule(
            interval_minutes=int(os.environ.get("TIP_INTERVAL_MINUTES", "30").strip()),
            window_start_minute=_parse_window_minute(
                os.environ.get("SEND_WINDOW_START", "09:00").strip(), allow_midnight_end=False
            ),
            window_end_minute=_parse_window_minute(
                os.environ.get("SEND_WINDOW_END", "24:00").strip(), allow_midnight_end=True
            ),
        )
    except ValueError as exc:
        raise SystemExit(
            f"发送节奏配置无效：{exc}\n"
            "请检查 .env 的 TIP_INTERVAL_MINUTES / SEND_WINDOW_START / SEND_WINDOW_END"
            "（格式见 .env.example）。"
        ) from exc
    return Config(
        app_id=app_id,
        app_secret=app_secret,
        target_group_openid=target_group_openid,
        schedule=schedule,
    )
