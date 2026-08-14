#!/usr/bin/env bash
# WSB 赢家推荐 (LangChain 版) — cron wrapper
# 继承原 wsb_winners.py 的 cron 约定:
#   - stdout 即消息 (无赢家时脚本静默/空输出)
#   - 非零退出码 = 失败 (cron 发送错误告警)
# 复用原 state/ticker 文件, 延续历史战绩。
#
# 部署位置: ~/.hermes/scripts/wsb_winners_langchain.sh (Hermes cron 引用)

set -uo pipefail

# 1. 加载 .env 获取 OPENROUTER_API_KEY (gateway 进程 env 里没有)
if [ -f "$HOME/.hermes/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$HOME/.hermes/.env"
  set +a
fi

cd "$(dirname "$0")/../../wsb-winners-langchain" || exit 1

export WSB_STATE_PATH="$HOME/.hermes/scripts/wsb_state.json"
export WSB_TICKER_FILE="$HOME/.hermes/scripts/wsb_tickers.txt"
# 默认模型, 512 max_tokens 已在 analyze.py 内固定
export WSB_MODEL="${WSB_MODEL:-deepseek/deepseek-v4-flash-0731}"

exec /home/vz/wsb-winners-langchain/.venv/bin/python -m wsb_winners.cli "$@"