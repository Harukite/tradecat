# -*- coding: utf-8 -*-
"""AI 服务配置模块 - 加载 config/.env"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # ai-service/src -> services -> tradecat
ENV_PATH = PROJECT_ROOT / "config" / ".env"

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(ENV_PATH)

# 添加 libs 到 path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 数据库路径
INDICATOR_DB = PROJECT_ROOT / "libs" / "database" / "services" / "telegram-service" / "market_data.db"

# Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

# 代理
HTTP_PROXY = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or "http://127.0.0.1:9910"
