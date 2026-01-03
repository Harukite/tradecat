# -*- coding: utf-8 -*-
"""
AI 分析 Telegram 交互模块
- 币种选择 -> 周期选择 -> 提示词选择 -> 触发 AI 分析
- 作为 telegram-service 的子模块集成
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from typing import Dict, List, Optional, TYPE_CHECKING

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
)

from src.prompt_registry import PromptRegistry
from src.process import run_process
from src.config import INDICATOR_DB

if TYPE_CHECKING:
    from telegram.ext import Application

logger = logging.getLogger(__name__)

# 会话状态
SELECTING_COIN, SELECTING_INTERVAL = range(2)

# 提示词注册表（全局单例）
prompt_registry = PromptRegistry()


def get_symbols_from_db() -> List[str]:
    """从 SQLite 数据库获取已有数据的币种列表"""
    try:
        conn = sqlite3.connect(str(INDICATOR_DB))
        cur = conn.cursor()
        
        # 从 MACD 表获取币种（最常用的指标表）
        tables = [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        
        symbols = set()
        for tbl in tables:
            try:
                cols = [d[1] for d in cur.execute(f"PRAGMA table_info('{tbl}')").fetchall()]
                sym_col = None
                for cand in ["交易对", "symbol", "Symbol"]:
                    if cand in cols:
                        sym_col = cand
                        break
                if sym_col:
                    rows = cur.execute(f"SELECT DISTINCT `{sym_col}` FROM '{tbl}'").fetchall()
                    for r in rows:
                        if r[0] and r[0].endswith("USDT"):
                            symbols.add(r[0])
                    if len(symbols) > 50:  # 找到足够多就停止
                        break
            except Exception:
                continue
        
        cur.close()
        conn.close()
        
        return sorted(symbols)
    except Exception as e:
        logger.error(f"从数据库获取币种失败: {e}")
        # 返回默认币种
        return [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
            "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
            "MATICUSDT", "LTCUSDT", "ATOMUSDT", "UNIUSDT", "APTUSDT",
        ]


class AIAnalysisHandler:
    """AI 分析的 Telegram 交互处理器"""

    def __init__(self, symbols_provider=None):
        """
        Args:
            symbols_provider: 可选的币种列表提供函数，如 telegram-service 的 get_active_symbols
        """
        self._symbols_provider = symbols_provider
        self._cached_symbols: List[str] = []
        self._cache_time = 0
        self.default_prompt = "市场全局解析"

    def get_supported_symbols(self) -> List[str]:
        """获取支持的币种列表"""
        import time
        now = time.time()
        
        # 5分钟缓存
        if self._cached_symbols and (now - self._cache_time) < 300:
            return self._cached_symbols
        
        # 优先使用外部提供的币种列表
        if self._symbols_provider:
            try:
                symbols = self._symbols_provider()
                if symbols:
                    self._cached_symbols = [s for s in symbols if s.endswith("USDT")]
                    self._cache_time = now
                    return self._cached_symbols
            except Exception as e:
                logger.warning(f"外部币种提供器失败: {e}")
        
        # 回退到从数据库获取
        self._cached_symbols = get_symbols_from_db()
        self._cache_time = now
        return self._cached_symbols

    # -------- 入口 --------
    async def start_ai_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """AI 分析入口"""
        context.user_data.setdefault("ai_prompt_name", self.default_prompt)
        context.user_data["ai_coin_page"] = 0
        return await self._show_coin_selection(update, context)

    # -------- 币种选择 --------
    async def handle_coin_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        if not query or not query.data:
            return ConversationHandler.END
        await query.answer()
        data = query.data

        if data == "ai_coin_prev":
            context.user_data["ai_coin_page"] = max(0, context.user_data.get("ai_coin_page", 0) - 1)
            return await self._show_coin_selection(update, context)
        if data == "ai_coin_next":
            context.user_data["ai_coin_page"] = context.user_data.get("ai_coin_page", 0) + 1
            return await self._show_coin_selection(update, context)

        if data == "ai_select_prompt":
            return await self._show_prompt_selection(update, context)
        if data.startswith("ai_set_prompt_"):
            return await self._handle_prompt_selected(update, context)

        if data.startswith("ai_coin_"):
            symbol = data.replace("ai_coin_", "")
            context.user_data["ai_selected_symbol"] = symbol
            return await self._show_interval_selection(update, context, symbol)

        if data == "ai_cancel":
            await query.edit_message_text("已取消 AI 分析")
            return ConversationHandler.END

        return ConversationHandler.END

    # -------- 周期选择 --------
    async def handle_interval_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        if not query or not query.data:
            return ConversationHandler.END
        await query.answer()
        data = query.data

        if data == "ai_back_to_coin":
            return await self._show_coin_selection(update, context)

        if data == "ai_select_prompt":
            return await self._show_prompt_selection(update, context)
        if data.startswith("ai_set_prompt_"):
            return await self._handle_prompt_selected(update, context)

        if data.startswith("ai_interval_"):
            interval = data.replace("ai_interval_", "")
            symbol = context.user_data.get("ai_selected_symbol")
            prompt_name = context.user_data.get("ai_prompt_name", self.default_prompt)
            if not symbol:
                await query.edit_message_text("❌ 未选择币种，请返回重新选择")
                return ConversationHandler.END
            
            await query.edit_message_text(f"🔄 正在分析 {symbol} @ {interval} ...\n⏳ 请稍候，AI 分析需要 30-60 秒")
            asyncio.create_task(self._run_analysis(update, context, symbol, interval, prompt_name))
            return ConversationHandler.END

        if data == "ai_cancel":
            await query.edit_message_text("已取消 AI 分析")
            return ConversationHandler.END

        return ConversationHandler.END

    # -------- 视图构建 --------
    async def _show_coin_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        symbols = self.get_supported_symbols()
        page = context.user_data.get("ai_coin_page", 0)
        per_page = 15
        total_pages = max(1, (len(symbols) + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        context.user_data["ai_coin_page"] = page
        page_symbols = symbols[page * per_page : (page + 1) * per_page]

        keyboard: List[List[InlineKeyboardButton]] = []
        # 每行5个币种
        for i in range(0, len(page_symbols), 5):
            row = [
                InlineKeyboardButton(sym.replace("USDT", ""), callback_data=f"ai_coin_{sym}")
                for sym in page_symbols[i : i + 5]
            ]
            keyboard.append(row)

        # 翻页
        keyboard.append([
            InlineKeyboardButton("⬅️", callback_data="ai_coin_prev"),
            InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="ai_page_info"),
            InlineKeyboardButton("➡️", callback_data="ai_coin_next"),
        ])

        # 提示词选择
        prompt_label = context.user_data.get("ai_prompt_name", self.default_prompt)
        keyboard.append([InlineKeyboardButton(f"🧠 {prompt_label}", callback_data="ai_select_prompt")])
        keyboard.append([InlineKeyboardButton("❌ 取消", callback_data="ai_cancel")])

        markup = InlineKeyboardMarkup(keyboard)
        text = f"🤖 AI 深度分析\n\n请选择币种（共 {len(symbols)} 个）"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        elif update.message:
            await update.message.reply_text(text, reply_markup=markup)
        return SELECTING_COIN

    async def _show_interval_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str) -> int:
        keyboard = [
            [
                InlineKeyboardButton("5m", callback_data="ai_interval_5m"),
                InlineKeyboardButton("15m", callback_data="ai_interval_15m"),
                InlineKeyboardButton("1h", callback_data="ai_interval_1h"),
                InlineKeyboardButton("4h", callback_data="ai_interval_4h"),
                InlineKeyboardButton("1d", callback_data="ai_interval_1d"),
            ],
            [
                InlineKeyboardButton("🔙 重选币种", callback_data="ai_back_to_coin"),
                InlineKeyboardButton("❌ 取消", callback_data="ai_cancel"),
            ],
        ]
        prompt_label = context.user_data.get("ai_prompt_name", self.default_prompt)
        text = f"🤖 AI 深度分析\n\n📌 币种: {symbol.replace('USDT','')}\n🧠 提示词: {prompt_label}\n\n请选择分析周期"
        markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        elif update.message:
            await update.message.reply_text(text, reply_markup=markup)
        return SELECTING_INTERVAL

    async def _show_prompt_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        if query:
            await query.answer()
        
        selected = context.user_data.get("ai_prompt_name", self.default_prompt)
        items = prompt_registry.list_prompts(grouped=False)
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for item in items:
            name = item["name"]
            label = item["title"]
            mark = " ✅" if name == selected else ""
            keyboard.append([InlineKeyboardButton(f"{label}{mark}", callback_data=f"ai_set_prompt_{name}")])
        
        if not keyboard:
            keyboard.append([InlineKeyboardButton("未找到提示词", callback_data="ai_select_prompt")])
        
        keyboard.append([InlineKeyboardButton("⬅️ 返回", callback_data="ai_back_to_coin")])
        markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("🧠 选择分析提示词", reply_markup=markup)
        return SELECTING_COIN

    async def _handle_prompt_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        if not query or not query.data:
            return ConversationHandler.END
        await query.answer()
        
        prompt_key = query.data.replace("ai_set_prompt_", "", 1)
        context.user_data["ai_prompt_name"] = prompt_key
        return await self._show_coin_selection(update, context)

    # -------- 分析执行 --------
    async def _run_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           symbol: str, interval: str, prompt: str):
        try:
            result = await run_process(symbol, interval, prompt)
            analysis_text = result.get("analysis", "未生成 AI 分析结果")
            
            # Telegram 消息限制 4096 字符
            if len(analysis_text) > 4000:
                # 分段发送
                parts = [analysis_text[i:i+4000] for i in range(0, len(analysis_text), 4000)]
                for i, part in enumerate(parts):
                    if i == 0:
                        if update.callback_query:
                            await update.callback_query.edit_message_text(part)
                        elif update.message:
                            await update.message.reply_text(part)
                    else:
                        if update.callback_query and update.callback_query.message:
                            await update.callback_query.message.reply_text(part)
                        elif update.message:
                            await update.message.reply_text(part)
            else:
                if update.callback_query:
                    await update.callback_query.edit_message_text(analysis_text)
                elif update.message:
                    await update.message.reply_text(analysis_text)
                    
        except Exception as exc:
            logger.exception("AI 分析失败")
            error_msg = f"❌ AI 分析失败：{exc}"
            if update.callback_query:
                await update.callback_query.edit_message_text(error_msg)
            elif update.message:
                await update.message.reply_text(error_msg)

    # -------- Handler 注册 --------
    def get_conversation_handler(self) -> ConversationHandler:
        """获取会话处理器，用于注册到 telegram-service"""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_ai_analysis, pattern="^start_ai_analysis$"),
            ],
            states={
                SELECTING_COIN: [
                    CallbackQueryHandler(self._show_prompt_selection, pattern="^ai_select_prompt$"),
                    CallbackQueryHandler(self._handle_prompt_selected, pattern="^ai_set_prompt_.*$"),
                    CallbackQueryHandler(self.handle_coin_selection, pattern="^ai_coin_.*$"),
                    CallbackQueryHandler(self.handle_coin_selection, pattern="^ai_cancel$"),
                    CallbackQueryHandler(lambda u, c: SELECTING_COIN, pattern="^ai_page_info$"),
                ],
                SELECTING_INTERVAL: [
                    CallbackQueryHandler(self.handle_interval_selection, pattern="^ai_interval_.*$"),
                    CallbackQueryHandler(self.handle_interval_selection, pattern="^ai_back_to_coin$"),
                    CallbackQueryHandler(self._show_prompt_selection, pattern="^ai_select_prompt$"),
                    CallbackQueryHandler(self._handle_prompt_selected, pattern="^ai_set_prompt_.*$"),
                    CallbackQueryHandler(self.handle_interval_selection, pattern="^ai_cancel$"),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.handle_coin_selection, pattern="^ai_cancel$"),
            ],
            name="ai_analysis",
            persistent=False,
        )


# -------- 模块级接口 --------
_handler_instance: Optional[AIAnalysisHandler] = None


def get_ai_handler(symbols_provider=None) -> AIAnalysisHandler:
    """获取 AI 分析处理器单例"""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = AIAnalysisHandler(symbols_provider)
    return _handler_instance


def register_ai_handlers(application: "Application", symbols_provider=None):
    """
    注册 AI 分析处理器到 telegram application
    
    用法（在 telegram-service 的 app.py 中）:
        from services.ai_service.src.bot.bot import register_ai_handlers
        register_ai_handlers(application, symbols_provider=self.get_active_symbols)
    """
    handler = get_ai_handler(symbols_provider)
    application.add_handler(handler.get_conversation_handler())
    logger.info("✅ AI 分析模块已注册")


__all__ = [
    "AIAnalysisHandler",
    "get_ai_handler", 
    "register_ai_handlers",
    "prompt_registry",
    "SELECTING_COIN",
    "SELECTING_INTERVAL",
]
