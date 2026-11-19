"""Tip List 加载：一行一条 Tip。"""

from __future__ import annotations

from pathlib import Path


def load_tips(path: Path) -> list[str]:
    """读取 Tip List，按文件顺序返回全部 Tip；空行与 # 注释行忽略。

    文件缺失时返回空列表（由调用方记警告并跳过发送）。
    """
    if not path.is_file():
        return []
    tips = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tips.append(stripped)
    return tips
