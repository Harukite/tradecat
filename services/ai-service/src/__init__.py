# -*- coding: utf-8 -*-
"""
AI 分析服务模块

作为 telegram-service 的子模块集成，提供 AI 深度分析功能。

用法（在 telegram-service 中）:
    import sys
    sys.path.insert(0, str(Path(__file__).parents[2] / "ai-service"))
    from src.bot import register_ai_handlers, get_ai_handler
    
    # 注册到 telegram application
    register_ai_handlers(application, symbols_provider=self.get_active_symbols)
"""
from src.bot import (
    AIAnalysisHandler,
    get_ai_handler,
    register_ai_handlers,
    prompt_registry,
)
from src.process import run_process

__all__ = [
    "AIAnalysisHandler",
    "get_ai_handler",
    "register_ai_handlers",
    "prompt_registry",
    "run_process",
]
