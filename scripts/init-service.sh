#!/bin/bash
# 初始化单个微服务的虚拟环境
# 用法: ./scripts/init-service.sh <service-name>
# 示例: ./scripts/init-service.sh data-service

set -e

SERVICE=$1
if [ -z "$SERVICE" ]; then
    echo "用法: $0 <service-name>"
    echo "可选: data-service | trading-service | telegram-service | order-service"
    exit 1
fi

SERVICE_DIR="services/$SERVICE"
if [ ! -d "$SERVICE_DIR" ]; then
    echo "❌ 服务目录不存在: $SERVICE_DIR"
    exit 1
fi

cd "$SERVICE_DIR"
echo "=== 初始化 $SERVICE ==="

# 创建虚拟环境
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活并安装依赖
source .venv/bin/activate
echo "安装依赖..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 复制配置文件
if [ -f "config/.env.example" ] && [ ! -f "config/.env" ]; then
    cp config/.env.example config/.env
    echo "已创建 config/.env，请编辑填入真实配置"
fi

echo "✅ $SERVICE 初始化完成"
echo "激活: cd $SERVICE_DIR && source .venv/bin/activate"
