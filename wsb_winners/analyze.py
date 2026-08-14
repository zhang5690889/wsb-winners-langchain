"""LangChain 核心: 用 LLM 结构化提取帖子分析结果。

用 `ChatPromptTemplate` + `ChatOpenAI.with_structured_output(PostAnalysis)`
替代原脚本的正则解析 —— 由 LLM 直接判断是否晒盈亏帖并给出金额/代码,
天然避免 "+18% vs $9,586" 这类正则误判。
"""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from . import config
from .models import PostAnalysis

logger = logging.getLogger(__name__)

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
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY 未设置(见 .env.example)")
    return ChatOpenAI(
        model=config.WSB_MODEL,
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        temperature=0,
        max_retries=2,
        timeout=60,
        max_tokens=512,
    )


def build_chain():
    """返回 LangChain runnable: (title, body) -> PostAnalysis。"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "标题: {title}\n\n正文(截断):\n{body}"),
    ])
    return prompt | build_llm().with_structured_output(PostAnalysis)


def analyze_post(chain, title: str, body: str, max_body: int = 1500) -> PostAnalysis:
    """分析单帖; LLM 失败时降级返回保守空分析(不当作赢家)。"""
    try:
        return chain.invoke({"title": title, "body": body[:max_body]})
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM 分析失败 (%s...): %s", title[:40], e)
        return PostAnalysis(is_gamble_post=False, gain=None, raw_gain=None, tickers=[])


def analyze_batch(chain, entries: list[dict], limit: Optional[int] = None) -> list[tuple[dict, PostAnalysis]]:
    """批量分析; limit>0 时可只分析前 N 条(测试用)。"""
    items = entries[:limit] if limit else entries
    return [(e, analyze_post(chain, e["title"], e["body"])) for e in items]