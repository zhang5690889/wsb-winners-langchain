"""RSS 抓取与解析(标准库 urllib + re, 无额外依赖)。"""
from __future__ import annotations

import html
import re
import time
import urllib.request

from . import config


def fetch_rss(url: str = config.RSS_URL, tries: int = 4) -> str | None:
    """带 UA 抓取 RSS; 429/失败按指数退避并轮换 UA; 返回文本或 None。"""
    for i in range(tries):
        ua = config.UAS[i % len(config.UAS)]
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": ua,
                "Accept": "application/atom+xml, application/xml, text/xml, */*",
                "Accept-Language": "en-US,en;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if i < tries - 1:
                time.sleep(15 * (2 ** i))  # 15s, 30s, 60s
            else:
                return None
    return None


def parse_entries(xml: str) -> list[dict]:
    """解析 Atom RSS, 返回 [{author, title, url, body, date}]。"""
    out = []
    regex_updated = re.compile(r"<updated>([^<]+)</updated>")
    for m in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
        e = m.group(1)
        name = re.search(r"<name>([^<]+)</name>", e)
        title = re.search(r"<title>([^<]+)</title>", e)
        link = re.search(r'<link href="([^"]+)"\s*/>', e)
        content = re.search(r"<content[^>]*>(.*?)</content>", e, re.S)
        updated = regex_updated.search(e)
        author = name.group(1).replace("/u/", "") if name else ""
        out.append({
            "author": author,
            "title": html.unescape(title.group(1)) if title else "",
            "url": html.unescape(link.group(1)) if link else "",
            "body": html.unescape(content.group(1)) if content else "",
            "date": (updated.group(1)[:10] if updated else config.TODAY),
        })
    return out