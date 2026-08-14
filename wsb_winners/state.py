"""JSON 状态管理: 每位作者的帖子历史与累计收益。

修复原脚本 bug: 去重只挡"历史重复 append", 不挡"今日候选收集"。
"""
from __future__ import annotations

import json
import os

from . import config
from .models import PostAnalysis, PostRecord


def load_state(path: str = config.STATE_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}}


def save_state(state: dict, path: str = config.STATE_PATH) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _record_exists(user_posts: list[dict], p: PostRecord) -> bool:
    """判断同(作者, 日期, 标题)历史是否已入库。"""
    return any(
        x.get("date") == p.date and x.get("title") == p.title
        for x in user_posts
    )


def update_state(state: dict, entry: dict, analysis: PostAnalysis) -> dict:
    """把一条(entry, analysis)写入 state。

    返回 {"appended": bool, "is_today": bool, "gainer": ...} 供候选选择使用。
    关键: appended=False(历史已有)不代表今天不能成为候选 —— is_today 单独判定。
    """
    users = state.setdefault("users", {})
    author = entry["author"]
    record = PostRecord(
        date=entry["date"],
        title=entry["title"][:140],
        url=entry["url"],
        gain=analysis.gain,
        raw_gain=analysis.raw_gain,
        tickers=analysis.tickers,
    )
    u = users.setdefault(author, {"posts": [], "total_gain": 0.0})
    appended = False
    if not _record_exists(u["posts"], record):
        u["posts"].append(record.model_dump())
        u["posts"] = u["posts"][-90:]
        if record.gain:
            u["total_gain"] = u.get("total_gain", 0.0) + record.gain
        appended = True
    is_today = entry["date"] >= config.TODAY
    return {
        "appended": appended,
        "is_today": is_today,
        "author": author,
        "record": record,
    }


def prune(state: dict) -> dict:
    """清理无帖子的用户。"""
    users = {k: v for k, v in state.get("users", {}).items() if v.get("posts")}
    state["users"] = users
    return state