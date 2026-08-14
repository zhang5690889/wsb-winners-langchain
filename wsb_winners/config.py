"""Global configuration for wsb-winners-langchain."""
from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# 本地时区日期(修复原脚本用 UTC 导致晚间运行漏掉当天帖子的 bug)
TODAY = datetime.now().astimezone().strftime("%Y-%m-%d")

# 赢家门槛: 历史累计盈利 >= 该金额才叫"之前赚钱多的人"
WINNER_TOTAL_MIN = float(os.environ.get("WSB_WINNER_TOTAL_MIN", "20000"))
# 今日新冒头(无历史但今天晒出大额盈利)
NEWCOMER_MIN = float(os.environ.get("WSB_NEWCOMER_MIN", "10000"))
# 最多推荐人数
MAX_CANDIDATES = int(os.environ.get("WSB_MAX_CANDIDATES", "6"))

# RSS 数据源
RSS_URL = os.environ.get("WSB_RSS_URL",
                         "https://www.reddit.com/r/wallstreetbets/new.rss?limit=100")

# LLM 配置(OpenRouter)
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL",
                                     "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
WSB_MODEL = os.environ.get("WSB_MODEL", "deepseek/deepseek-v4-flash-0731")

# 路径
HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.environ.get("WSB_STATE_PATH",
                            os.path.join(HERE, "..", "wsb_state.json"))
TICKER_FILE = os.environ.get("WSB_TICKER_FILE",
                             os.path.join(HERE, "..", "wsb_tickers.txt"))
MAIL_TO = os.environ.get("WSB_MAIL_TO", "xinwen.zhang.911@gmail.com")

# 邮件 CLI(复用 google-workspace skill)
GMAIL_CLI = os.environ.get(
    "GMAIL_CLI",
    os.path.expanduser(
        "~/.hermes/skills/productivity/google-workspace/scripts/google_api.py"))

# UA 轮换
UAS = [
    ("Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0 "
     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
     "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"),
]