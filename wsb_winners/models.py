"""Pydantic schemas used across the pipeline."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PostAnalysis(BaseModel):
    """LLM 结构化输出: 单条 WSB 帖子的分析结果。

    gain 语义: 该帖晒出的收益金额(美元)。亏损为负, 未晒金额为 None。
    raw_gain: 原文中的金额描述, 如 "up $9,586 (+18%)" 或 "$13K+ in a morning"。
    """

    is_gamble_post: bool = Field(
        description="是否为个人晒盈亏/投机帖(YOLO/Gains/Loss/晒账户), 而不是企业新闻")
    gain: Optional[float] = Field(
        default=None,
        description="该帖明确晒出的收益金额(美元, 亏损为负数)。未晒金额则为 null。"
                    "注意百分比(+18%)不是金额, 不计入")
    raw_gain: Optional[str] = Field(
        default=None,
        description="原文中给出收益金额的原样片段, 如 'up $9,586 (+18%)'")
    tickers: list[str] = Field(
        default_factory=list,
        description="帖子里提到的股票代码列表(如 $AAPL / **TSLA** / GME), 仅真实美股代码")


class PostRecord(BaseModel):
    """入库的历史帖子记录(JSON state 的一项)。"""

    date: str
    title: str
    url: str
    gain: Optional[float] = None
    raw_gain: Optional[str] = None
    tickers: list[str] = Field(default_factory=list)


class Winner(BaseModel):
    """一个赢家候选。"""

    author: str
    total_gain: float = 0.0
    today_gain: Optional[float] = None
    raw_gain: Optional[str] = None
    tickers: list[str] = Field(default_factory=list)
    title: str = ""
    url: str = ""
    badge: str = "🆕"