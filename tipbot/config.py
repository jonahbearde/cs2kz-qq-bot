"""配置装载：凭据与 Target Group 标识全部来自 .env。

QQ 适配层的一部分，保持极薄，不做单元测试（按手册人工验收）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    app_id: str
    app_secret: str
    # 空字符串 = 未配置 Target Group：机器人只捕获群标识，不发送。
    target_group_openid: str


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
    return Config(
        app_id=app_id,
        app_secret=app_secret,
        target_group_openid=target_group_openid,
    )
