"""报告生成: 中文推荐文本 + HTML 邮件正文。"""
from __future__ import annotations

import html as html_mod

from . import config
from .models import Winner
from .select import hot_tickers


def _badge(w: Winner) -> str:
    """🏆 = 历史累计赢家; 🆕 = 今日新冒头。"""
    return "🏆" if w.total_gain >= config.WINNER_TOTAL_MIN else "🆕"


def _display_name(author: str) -> str:
    return author if author and author != "[deleted]" else "deleted_user"


def build_text_report(winners: list[Winner], hot: list[tuple[str, int]]) -> str:
    lines = [f"💹 **WSB 赢家推荐 — {config.TODAY}**", ""]
    for w in winners:
        uname = _display_name(w.author)
        hist = f"累计 +${w.total_gain:,.0f}" if w.total_gain > 0 else f"累计 ${w.total_gain:,.0f}"
        tday = f"今日 {w.raw_gain}" if w.raw_gain else "今日未晒数额"
        tl = ", ".join(w.tickers)
        lines.append(f"{_badge(w)} **{uname}** ({hist} | {tday})")
        lines.append(f"   📈 提到: {tl}")
        lines.append(f"   {w.title[:100]}")
        lines.append(f"   🔗 {w.url}")
        lines.append("")
    if hot:
        hot_str = ", ".join(f"{t}({n})" for t, n in hot)
        lines.append(f"🔥 **热门提及**: {hot_str}")
    lines.append("⚠️ 内容来自 WSB 帖子, 仅供娱乐, 不构成投资建议")
    return "\n".join(lines)


def build_html_report(winners: list[Winner], hot: list[tuple[str, int]]) -> str:
    """把文本报告转成简单 HTML 邮件正文。"""
    esc = html_mod.escape(build_text_report(winners, hot))
    esc = esc.replace("\n", "<br>")
    return (
        "<html><body style=\"font-family:Arial,sans-serif;font-size:14px;"
        f"line-height:1.6\">{esc}</body></html>"
    )


def build_subject() -> str:
    return f"💹 WSB 赢家推荐 — {config.TODAY}"