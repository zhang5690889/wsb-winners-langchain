"""单元测试: 纯逻辑部分(不需 LLM / 网络)。"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wsb_winners import config  # noqa: E402
from wsb_winners import fetch, report, select, state  # noqa: E402
from wsb_winners.models import PostAnalysis, Winner  # noqa: E402


class TestFetch:
    def test_parse_entries_basic(self):
        xml = """<?xml version="1.0"?>
<feed>
<entry><author><name>/u/alice</name></author>
<title>YOLO +$25,000 in GME</title>
<link href="https://reddit.com/r/wallstreetbets/comments/abc"/>
<content type="html">just yolo&#39;d</content>
<updated>2026-08-13T10:00:00+00:00</updated></entry>
<entry><author><name>/u/bob</name></author>
<title>TSLA earnings beat</title>
<link href="https://reddit.com/r/wallstreetbets/comments/def"/>
<content type="html">revenue up</content>
<updated>2026-08-12T10:00:00+00:00</updated></entry>
</feed>"""
        entries = fetch.parse_entries(xml)
        assert len(entries) == 2
        assert entries[0]["author"] == "alice"
        assert entries[0]["title"] == "YOLO +$25,000 in GME"
        assert entries[0]["date"] == "2026-08-13"
        assert "yolo'd" in entries[0]["body"]
        assert entries[1]["date"] == "2026-08-12"


class TestState:
    def _mk(self):
        return {"users": {}}

    def _entry(self, author="alice", title="YOLO +$10k", date="2026-08-13"):
        return {"author": author, "title": title, "url": "https://x", "date": date}

    def test_update_and_dedup_keeps_today_flag(self):
        st = self._mk()
        a = PostAnalysis(is_gamble_post=True, gain=10000, raw_gain="+$10k",
                         tickers=["GME"])
        r1 = state.update_state(st, self._entry(), a)
        assert r1["appended"] is True
        assert r1["is_today"] is True
        # 同帖再入库: appended=False (去重), 但 is_today 仍 True
        r2 = state.update_state(st, self._entry(), a)
        assert r2["appended"] is False
        assert r2["is_today"] is True
        # 累计只算一次
        assert st["users"]["alice"]["total_gain"] == 10000
        assert len(st["users"]["alice"]["posts"]) == 1

    def test_dedup_no_miss_for_candidate_selection(self):
        """去重不应把已入库的今日帖子排除出候选计算。"""
        st = self._mk()
        a = PostAnalysis(is_gamble_post=True, gain=10000, raw_gain="+$10k",
                         tickers=["GME"])
        state.update_state(st, self._entry(), a)  # 首次入库
        # 再次 update 同一帖 -> appended False 但 is_today True
        r2 = state.update_state(st, self._entry(), a)
        winners = select.select_winners(st, [r2])
        assert len(winners) == 1
        assert winners[0].author == "alice"

    def test_not_today_excluded(self):
        st = self._mk()
        a = PostAnalysis(is_gamble_post=True, gain=10000, tickers=["GME"])
        entry = self._entry(date="2026-08-10")
        r = state.update_state(st, entry, a)
        assert r["is_today"] is False
        winners = select.select_winners(st, [r])
        assert winners == []

    def test_no_ticker_no_win(self):
        st = self._mk()
        a = PostAnalysis(is_gamble_post=True, gain=999999, tickers=[])
        r = state.update_state(st, self._entry(), a)
        assert select.select_winners(st, [r]) == []


class TestSelect:
    def test_newcomer_threshold(self):
        st = {"users": {"u1": {"posts": [], "total_gain": 0.0}}}
        rec = type("R", (), {
            "tickers": ["TSLA"], "gain": 15000, "raw_gain": "+$15k",
            "title": "TSLA yolo", "url": "https://x",
        })()
        r = {"is_today": True, "author": "u1", "record": rec}
        winners = select.select_winners(st, [r])
        assert len(winners) == 1
        assert winners[0].badge == "🆕"
        assert winners[0].tickers == ["TSLA"]

    def test_threshold_below(self):
        st = {"users": {"u1": {"posts": [], "total_gain": 0.0}}}
        rec = type("R", (), {
            "tickers": ["TSLA"], "gain": 9000, "raw_gain": None,
            "title": "", "url": "",
        })()
        r = {"is_today": True, "author": "u1", "record": rec}
        assert select.select_winners(st, [r]) == []

    def test_hot_tickers(self):
        ws = [
            Winner(author="a", tickers=["GME", "TSLA"]),
            Winner(author="b", tickers=["GME"]),
            Winner(author="c", tickers=["TSLA", "GME"]),
        ]
        hot = select.hot_tickers(ws)
        assert hot[0] == ("GME", 3)
        assert hot[1] == ("TSLA", 2)


class TestReport:
    def test_build_text(self):
        ws = [Winner(author="alice", total_gain=25000, today_gain=12000,
                     raw_gain="+$12k", tickers=["GME"],
                     title="GME to the moon", url="https://x")]
        txt = report.build_text_report(ws, [("GME", 1)])
        assert "WSB 赢家推荐" in txt
        assert "🏆" in txt          # total >= 20k
        assert "alice" in txt
        assert "GME" in txt
        assert "https://x" in txt

    def test_build_html(self):
        ws = [Winner(author="bob", total_gain=1000, today_gain=11000,
                     raw_gain="+$11k", tickers=["TSLA"],
                     title="TSLA yolo", url="https://x")]
        html = report.build_html_report(ws, [])
        assert html.startswith("<html>")
        assert "TSLA" in html