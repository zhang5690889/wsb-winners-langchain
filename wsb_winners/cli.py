"""CLI 入口: 抓 RSS → LLM 分析 → 更新状态 → 选赢家 → (可选)发邮件。

用法:
    python -m wsb_winners.cli                 # 正式: 分析+发邮件+一行状态
    python -m wsb_winners.cli --dry-run       # 只打印报告, 不发邮件
    python -m wsb_winners.cli --dry-run --limit 10   # 只分析前 10 条
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="WSB 赢家推荐 (LangChain 版)")
    ap.add_argument("--dry-run", action="store_true", help="只打印报告, 不发邮件")
    ap.add_argument("--limit", type=int, default=0, help="只分析前 N 条 RSS(测试用)")
    args = ap.parse_args(argv)

    from . import config, fetch, report, select, state
    from .analyze import analyze_batch, build_chain
    from .email_send import send_email

    xml = fetch.fetch_rss()
    if not xml:
        print("❌ WSB 赢家抓取失败: RSS 无法获取", file=sys.stderr)
        return 1
    entries = fetch.parse_entries(xml)
    if not entries:
        return 0

    chain = build_chain()
    st = state.load_state()

    today_results = []
    analyzed = 0
    for entry, analysis in analyze_batch(chain, entries,
                                         limit=args.limit or None):
        analyzed += 1
        r = state.update_state(st, entry, analysis)
        today_results.append(r)

    st = state.prune(st)
    state.save_state(st)

    winners = select.select_winners(st, today_results)
    if not winners:
        # 与旧版一致: 无赢家 → 静默退出, 不推送不发送
        return 0

    hot = select.hot_tickers(winners)
    report_text = report.build_text_report(winners, hot)
    subject = report.build_subject()

    if args.dry_run:
        print(f"[dry-run] 分析 {analyzed} 帖, 候选 {len(winners)} 位:")
        print()
        print(report_text)
        return 0

    ok, err = send_email(subject, report.build_html_report(winners, hot))
    if not ok:
        print(f"❌ WSB 推荐邮件发送失败: {err}", file=sys.stderr)
        print(f"❌ WSB 赢家推荐邮件发送失败({config.TODAY}) — 详见日志")
        return 1

    names = ", ".join(w.author if w.author and w.author != "[deleted]"
                      else "deleted_user" for w in winners)
    print(f"✅ WSB 赢家推荐已发邮箱 — {config.TODAY} · {len(winners)}位: {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())