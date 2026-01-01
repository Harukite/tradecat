#!/bin/bash
# 初始化所有微服务的虚拟环境
# 用法: ./scripts/init-all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

for SERVICE in data-service trading-service telegram-service order-service; do
    echo ""
    bash scripts/init-service.sh "$SERVICE"
done

echo ""
echo "=== 全部初始化完成 ==="
echo "请编辑各服务的 config/.env 文件填入真实配置"
