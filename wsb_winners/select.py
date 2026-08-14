"""赢家选择: 历史赢家(累计>=门槛) 或 今日新晒大额盈利。"""
from __future__ import annotations

from collections import defaultdict

from . import config
from .models import Winner


def select_winners(state: dict, today_results: list[dict]) -> list[Winner]:
    """today_results: [update_state(...) 返回的 dict]; 已含 is_today 标记。

    候选条件: 帖子提到真实 ticker, 且 (该作者历史累计 >= WINNER_TOTAL_MIN
    或 今日该帖 gain >= NEWCOMER_MIN)。同作者同日只取一条。
    """
    users = state.get("users", {})
    cands: dict[str, Winner] = {}
    for r in today_results:
        if not r["is_today"]:
            continue
        rec = r["record"]
        if not rec.tickers:
            continue
        total = users.get(r["author"], {}).get("total_gain", 0.0)
        if total >= config.WINNER_TOTAL_MIN or (rec.gain or 0) >= config.NEWCOMER_MIN:
            if r["author"] in cands:
                continue
            cands[r["author"]] = Winner(
                author=r["author"],
                total_gain=total,
                today_gain=rec.gain,
                raw_gain=rec.raw_gain,
                tickers=rec.tickers,
                title=rec.title,
                url=rec.url,
                badge="🏆" if total >= config.WINNER_TOTAL_MIN else "🆕",
            )

    winners = sorted(
        cands.values(),
        key=lambda w: (w.total_gain, w.today_gain or 0),
        reverse=True,
    )[: config.MAX_CANDIDATES]
    return winners


def hot_tickers(winners: list[Winner], top: int = 5) -> list[tuple[str, int]]:
    """候选中最常被提及的 ticker 热度榜。"""
    counts: dict[str, int] = defaultdict(int)
    for w in winners:
        for t in w.tickers:
            counts[t] += 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[:top]