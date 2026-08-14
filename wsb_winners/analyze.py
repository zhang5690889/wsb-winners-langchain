"""LangChain 核心: 用 LLM 结构化提取帖子分析结果。

用 `ChatPromptTemplate` + `ChatOpenAI.with_structured_output(PostAnalysis)`
替代原脚本的正则解析 —— 由 LLM 直接判断是否晒盈亏帖并给出金额/代码,
天然避免 "+18% vs $9,586" 这类正则误判。

带规则预筛层: 标题明显不含金额/晒盈亏特征时跳过 LLM(省时省钱),
只有疑似帖子才调用 LLM 精细解析。
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from . import config
from .models import PostAnalysis

logger = logging.getLogger(__name__)

# 快速预筛: 标题含以下特征才值得调 LLM(与旧脚本 is_gamble_post 同思路)
_PRE_FILTER_RE = re.compile(
    r"YOLO|GAIN|LOSS|P/L|\bPL\b|POSITION|LOST|PROFIT|\bAMA\b|PORTFOLIO|ACCOUNT|"
    r"\$| DOLLAR|->|→|[+\-−]\s*\$?\s*[\d.,]+\s*[kKmMbB]?",
    re.I,
)
# 企业新闻特征(即使带 $ 也不用调 LLM, 标题直接排除)
_NEWS_RE = re.compile(
    r"BILLION|TRILLION|LINES UP|SIGNS|STRIKES|RAISES|FINANCING| DEAL|FUNDING|"
    r"ACQUIRES| PLAN|BOARD|REPORTS|EARNINGS|GUIDANCE| OFFER|SEC|FILES|WINS|WON",
    re.I,
)

SYSTEM_PROMPT = """你是 r/wallstreetbets 帖子分析器。输入一条 WSB 帖子的标题和正文, 输出结构化分析:

1. is_gamble_post: 是否为"个人晒盈亏/投机帖"。典型特征: 标题/正文含 YOLO、Gain(s)、Loss、
   P/L、Position、晒账户余额、晒期权/股票仓位盈亏。企业新闻(财报、融资、收购、SEC 公告、
   "$X billion deal")不算。
2. gain: 帖子明确晒出的收益金额(美元, 亏损用负数)。只取明确数字:
   - 优先取"收益词后的金额"(up $9,586 / gains +$10k / profit $50k / made $50k)
   - 其次取带符号金额(+$1.2M / -$20k / -$3,200)
   - 百分比(+18%, up 12%)不是金额, 不要当成 gain
   - 若帖子没有晒出金额(只是喊单/观点), gain 为 null
   注意: 裸数字可能是入场价($227.69)、仓位价值($53,279)而非收益, 没有收益词或符号时不要猜。
3. raw_gain: 原文中给出 gain 的片段(如 "up $9,586 (+18%)"), 无则 null。
4. tickers: 帖子提到的真实美股代码列表。识别 $AAPL、**TSLA**、裸词 GME 等; 过滤日常英文词
   (UP, LOSS, GAIN, YOLO 等)和常见干扰词。纯观点帖(没说任何具体代码)给空列表。

只输出 JSON 对象, 不要多余文字。"""


def build_llm() -> ChatOpenAI:
    """按 LLM_GATEWAY 选择 endpoint 与 key。

    tokenrouter(默认): 走 TOKENROUTER_API_KEY + DeepSeek Pro。
    openrouter: 走 OPENROUTER_API_KEY, 可配 WSB_MODEL 用免费模型。
    """
    if config.LLM_GATEWAY == "openrouter":
        api_key = config.OPENROUTER_API_KEY
        base_url = config.OPENROUTER_BASE_URL
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY 未设置(见 .env.example)")
    else:
        api_key = config.TOKENROUTER_API_KEY
        base_url = config.TOKENROUTER_BASE_URL
        if not api_key:
            raise RuntimeError("TOKENROUTER_API_KEY 未设置(见 .env.example)")
    return ChatOpenAI(
        model=config.WSB_MODEL,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        max_retries=2,
        timeout=90,
        max_tokens=1024,
    )


def build_chain():
    """返回 LangChain runnable: (title, body) -> PostAnalysis。"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "标题: {title}\n\n正文(截断):\n{body}"),
    ])
    return prompt | build_llm().with_structured_output(PostAnalysis)


def _should_call_llm(title: str) -> bool:
    """规则预筛: 标题有明显晒盈亏特征且不像企业新闻才值得调 LLM。"""
    if not _PRE_FILTER_RE.search(title):
        return False
    if _NEWS_RE.search(title):
        return False
    return True


def analyze_post(chain, title: str, body: str, max_body: int = 1500) -> PostAnalysis:
    """分析单帖; LLM 失败时降级返回保守空分析(不当作赢家)。"""
    try:
        return chain.invoke({"title": title, "body": body[:max_body]})
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM 分析失败 (%s...): %s", title[:40], e)
        return PostAnalysis(is_gamble_post=False, gain=None, raw_gain=None, tickers=[])


def analyze_batch(chain, entries: list[dict], limit: Optional[int] = None) -> list[tuple[dict, PostAnalysis]]:
    """批量分析; limit>0 时可只分析前 N 条(测试用)。

    规则预筛: 标题不含晒盈亏特征/含企业新闻特征 → 直接降级为空分析, 不调 LLM。
    """
    items = entries[:limit] if limit else entries
    results = []
    for e in items:
        if _should_call_llm(e["title"]):
            results.append((e, analyze_post(chain, e["title"], e["body"])))
        else:
            results.append((e, PostAnalysis(is_gamble_post=False)))
    return results