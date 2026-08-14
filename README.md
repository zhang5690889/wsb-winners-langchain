# WSB Winners — LangChain Edition

每天抓取 r/wallstreetbets 最新 100 帖,用 **LangChain + LLM 结构化提取**识别晒盈亏
(YOLO/Gains/Loss)的帖子,提取收益金额与提到的股票代码,按"历史赢家 / 今日大额新秀"
门槛挑选赢家,生成中文推荐并通过 Gmail 发送。

> 这是 `~/.hermes/scripts/wsb_winners.py` 的 LangChain 重写版,修复了原脚本的
> 金额解析、UTC 时区、去重误伤今日候选三个 bug。

## 架构

```
fetch_rss ──► analyze(LLM) ──► update_state ──► select_winners ──► build_report ──► send_email
```

| 模块 | 说明 |
|------|------|
| `fetch` | RSS 抓取(UA 轮换 + 指数退避,标准库 urllib) |
| `analyze` | **LangChain chain**: `PromptTemplate → ChatOpenAI.with_structured_output(PostAnalysis)` |
| `models` | Pydantic 结构化输出:is_gamble_post / gain / raw_gain / tickers |
| `state` | JSON 状态(每位作者历史战绩),去重只挡历史 append,不误伤今日候选 |
| `select` | 门槛选择:历史累计 ≥ $20k(🏆)或今日单笔 ≥ $10k(🆕),最多 6 位 |
| `report` | 中文推荐文本 + HTML 邮件正文 |
| `email_send` | 复用 google-workspace 的 google_api.py Gmail CLI |
| `cli` | 入口,支持 `--dry-run` 与 `--limit N` |

## 安装

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env    # 填入 OPENROUTER_API_KEY
```

## 用法

```bash
# 干跑:抓 RSS + LLM 分析 + 选赢家,只打印报告,不发邮件
python -m wsb_winners.cli --dry-run

# 干跑,只分析前 10 条(快速验证)
python -m wsb_winners.cli --dry-run --limit 10

# 正式:分析 → 发邮件 → 打印一行状态
python -m wsb_winners.cli
```

## 配置(环境变量)

| 变量 | 默认 | 说明 |
|------|------|------|
| `OPENROUTER_API_KEY` | — | OpenRouter key(必需) |
| `WSB_MODEL` | `deepseek/deepseek-v4-flash-0731` | LLM 模型 |
| `WSB_STATE_PATH` | `wsb_state.json` | 状态文件 |
| `WSB_TICKER_FILE` | `wsb_tickers.txt` | 美股白名单 |
| `WSB_MAIL_TO` | `xinwen.zhang.911@gmail.com` | 收件人 |

## 测试

```bash
python -m pytest tests/ -v
```

⚠️ 内容来自 WSB 帖子,仅供娱乐,不构成投资建议。