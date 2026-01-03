#!/bin/bash
# ai-service 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$SERVICE_DIR")")"

cd "$SERVICE_DIR"

# 加载全局配置
if [ -f "$PROJECT_ROOT/config/.env" ]; then
    set -a
    source "$PROJECT_ROOT/config/.env"
    set +a
fi

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 检查代理
if [ -n "$HTTP_PROXY" ]; then
    echo "✓ 代理可用: $HTTP_PROXY"
fi

case "$1" in
    test)
        # 测试数据获取
        python3 -c "
from src.data.fetcher import fetch_payload
import json
payload = fetch_payload('BTCUSDT', '15m')
print('K线周期:', list(payload.get('candles', {}).keys()))
print('期货数据条数:', len(payload.get('metrics', [])))
print('指标表数:', len(payload.get('indicators', {})))
"
        ;;
    analyze)
        # 运行分析
        symbol="${2:-BTCUSDT}"
        interval="${3:-15m}"
        prompt="${4:-深度报告}"
        python3 -c "
import asyncio
from src.pipeline import run_analysis
result = asyncio.run(run_analysis('$symbol', '$interval', '$prompt'))
if result.get('error'):
    print('错误:', result['error'])
else:
    print(result['analysis'])
"
        ;;
    *)
        echo "用法: $0 {test|analyze [symbol] [interval] [prompt]}"
        echo ""
        echo "示例:"
        echo "  $0 test                    # 测试数据获取"
        echo "  $0 analyze BTCUSDT 15m     # 分析 BTC 15分钟"
        ;;
esac
