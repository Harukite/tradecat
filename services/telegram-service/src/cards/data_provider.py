#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""排行榜数据访问层

数据源：market_data.db（每个指标一张表）
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from utils.paths import 获取数据服务CSV目录


LOGGER = logging.getLogger(__name__)

# 新旧表名映射，保证卡片仍可使用历史名称访问
TABLE_NAME_MAP = {
    # 映射到数据库中的真实表名（含 .py）；CSV 采用多重候选自动匹配
    "基础数据": "基础数据同步器.py",
    "ATR波幅榜单": "ATR波幅扫描器.py",
    "ATR波幅扫描器.py": "ATR波幅扫描器.py",
    "BB榜单": "布林带扫描器.py",
    "布林带榜单": "布林带扫描器.py",
    "布林带扫描器.py": "布林带扫描器.py",
    "CVD榜单": "CVD信号排行榜.py",
    "CVD信号排行榜.py": "CVD信号排行榜.py",
    "KDJ随机指标榜单": "KDJ随机指标扫描器.py",
    "KDJ随机指标扫描器.py": "KDJ随机指标扫描器.py",
    "K线形态榜单": "K线形态扫描器.py",
    "K线形态扫描器.py": "K线形态扫描器.py",
    "MACD柱状榜单": "MACD柱状扫描器.py",
    "MACD柱状扫描器.py": "MACD柱状扫描器.py",
    "MFI资金流量榜单": "MFI资金流量扫描器.py",
    "MFI资金流量扫描器.py": "MFI资金流量扫描器.py",
    "OBV能量潮榜单": "OBV能量潮扫描器.py",
    "OBV能量潮扫描器.py": "OBV能量潮扫描器.py",
    "VPVR榜单": "VPVR排行生成器.py",
    "VPVR排行生成器.py": "VPVR排行生成器.py",
    "VWAP榜单": "VWAP离线信号扫描.py",
    "VWAP离线信号扫描.py": "VWAP离线信号扫描.py",
    "主动买卖比榜单": "主动买卖比扫描器.py",
    "主动买卖比扫描器.py": "主动买卖比扫描器.py",
    "成交量比率榜单": "成交量比率扫描器.py",
    "成交量比率扫描器.py": "成交量比率扫描器.py",
    "支撑阻力榜单": "全量支撑阻力扫描器.py",
    "全量支撑阻力扫描器.py": "全量支撑阻力扫描器.py",
    "收敛发散榜单": "G，C点扫描器.py",
    "G，C点扫描器.py": "G，C点扫描器.py",
    "流动性榜单": "流动性扫描器.py",
    "流动性扫描器.py": "流动性扫描器.py",
    "谐波信号榜单": "谐波信号扫描器.py",
    "谐波信号扫描器.py": "谐波信号扫描器.py",
    "趋势线榜单": "趋势线榜单",
    # 无扩展名 -> .py 映射，避免 SELECT 失败
    "布林带扫描器": "布林带扫描器.py",
    "成交量比率扫描器": "成交量比率扫描器.py",
    "主动买卖比扫描器": "主动买卖比扫描器.py",
    "全量支撑阻力扫描器": "全量支撑阻力扫描器.py",
    "KDJ随机指标扫描器": "KDJ随机指标扫描器.py",
    "MACD柱状扫描器": "MACD柱状扫描器.py",
    "OBV能量潮扫描器": "OBV能量潮扫描器.py",
    "谐波信号扫描器": "谐波信号扫描器.py",
    "基础数据同步器": "基础数据同步器.py",
    "G，C点扫描器": "G，C点扫描器.py",
    "流动性扫描器": "流动性扫描器.py",
    "MFI资金流量扫描器": "MFI资金流量扫描器.py",
    "CVD信号排行榜": "CVD信号排行榜.py",
    "VWAP离线信号扫描": "VWAP离线信号扫描.py",
    "VPVR排行生成器": "VPVR排行生成器.py",
    "K线形态扫描器": "K线形态扫描器.py",
    "ATR波幅扫描器": "ATR波幅扫描器.py",
    "大资金操盘扫描器": "大资金操盘扫描器.py",
    "智能RSI扫描器": "智能RSI扫描器.py",
    "超级精准趋势扫描器": "超级精准趋势扫描器.py",
    "趋势线榜单.py": "趋势线榜单.py",
    "趋势线榜单": "趋势线榜单.py",
    "期货情绪聚合表": "期货情绪聚合表.py",
    "期货情绪聚合榜单": "期货情绪聚合榜单",
    "期货情绪元数据": "期货情绪元数据",
}


def format_symbol(sym: str) -> str:
    """将交易对显示为基础币种（去除 USDT 后缀），保持大写."""
    s = (sym or "").strip().upper()
    for suffix in ("USDT",):
        if s.endswith(suffix):
            return s[: -len(suffix)] or s
    return s


def _normalize_period_value(period: str) -> str:
    """
    统一周期表达：数据库里存在 `1d`，而业务层普遍使用 `24h`。
    这里做双向映射，确保过滤时不因为字符串差异导致数据缺失。
    """
    p = (period or "").strip().lower()
    alias = {
        "1d": "24h",
        "24h": "1d",
        "1day": "1d",
        "1w": "1w",
    }
    return alias.get(p, p)


def _period_to_db(period: str) -> str:
    """将业务周期转为数据库存储格式"""
    p = (period or "").strip().lower()
    return {"24h": "1d", "1day": "1d"}.get(p, p)



# ============================================================
# RankingDataProvider（market_data.db）
# ============================================================
class RankingDataProvider:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        # 优先使用 telegram-service 内部的数据库
        _local_db = Path(__file__).resolve().parent.parent.parent / "data" / "market_data.db"
        self.db_path = db_path or (_local_db if _local_db.exists() else 获取数据服务CSV目录() / "market_data.db")
        self.csv_root = Path(__file__).resolve().parent.parent.parent / "data"

    # ---------------- 内部工具 ----------------
    def _connect(self) -> Optional[sqlite3.Connection]:
        if not self.db_path.exists():
            LOGGER.warning("market_data.db 不存在，回退 CSV: %s", self.db_path)
            return None
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            # 只读模式下避免修改 journal_mode，其他 PRAGMA 做容错设置
            for pragma in (
                "synchronous=OFF",
                "temp_store=MEMORY",
                "mmap_size=134217728",  # 128MB 映射
            ):
                try:
                    conn.execute(f"PRAGMA {pragma};")
                except Exception as pragma_exc:  # pragma: no cover
                    LOGGER.debug("设置 PRAGMA %s 失败，忽略: %s", pragma, pragma_exc)
            return conn
        except Exception as exc:  # pragma: no cover - 防御性兜底
            LOGGER.warning("打开 SQLite 失败，回退 CSV: %s", exc)
            return None

    def _resolve_table(self, name: str) -> str:
        return TABLE_NAME_MAP.get(name, name)

    def _load_table(self, table: str) -> List[sqlite3.Row]:
        table = self._resolve_table(table)
        conn = self._connect()
        if conn is None:
            return []
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT * FROM '{table}'")
            rows = cur.fetchall()
            return rows
        except Exception as exc:
            LOGGER.warning("读取表 %s 失败: %s", table, exc)
            return []
        finally:
            conn.close()

    def _load_table_period(self, table: str, period: str) -> List[sqlite3.Row]:
        """按周期精准读取表，减少全表扫描；若列不存在则回退全表。"""
        table = self._resolve_table(table)
        conn = self._connect()
        if conn is None:
            return []
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            # 检查是否有 周期/period 列
            cur.execute(f"PRAGMA table_info('{table}')")
            cols = [row[1] for row in cur.fetchall()]
            period_cols = [c for c in cols if c in ("周期", "period", "PERIOD")]
            if not period_cols:
                cur.execute(f"SELECT * FROM '{table}'")
                return cur.fetchall()

            target = _normalize_period_value(period)
            # 兼容大小写/别名
            cand = list({target, target.upper(), period, period.lower(), period.upper()})
            placeholders = ",".join("?" for _ in cand)
            where = " OR ".join([f"{col} IN ({placeholders})" for col in period_cols])
            cur.execute(f"SELECT * FROM '{table}' WHERE {where}", cand * len(period_cols))
            return cur.fetchall()
        except Exception as exc:
            LOGGER.warning("读取表 %s 按周期筛选失败，回退全表: %s", table, exc)
            try:
                cur.execute(f"SELECT * FROM '{table}'")
                return cur.fetchall()
            except Exception:
                return []
        finally:
            conn.close()

    def _fetch_single_row(self, table: str, period: str, symbol: str) -> Dict:
        """按周期+交易对精准取一行，降 IO/CPU。"""
        table = self._resolve_table(table)
        conn = self._connect()
        if conn is None:
            return {}
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        norm_p = _normalize_period_value(period)
        # 兼容交易对/去 USDT / symbol 多列
        sym_full = symbol.upper()
        sym_with_usdt = sym_full + "USDT"
        try:
            # 检查可用列
            cur.execute(f"PRAGMA table_info('{table}')")
            cols = [row[1] for row in cur.fetchall()]
            period_cols = [c for c in cols if c.lower() in ("周期", "period", "interval")]

            # 组合符号匹配条件
            sym_where = """
                (upper(交易对)=?
                 OR replace(upper(交易对),'USDT','')=?
                 OR upper(币种)=?
                 OR upper(symbol)=?
                )
            """
            sym_params = (sym_with_usdt, sym_full, sym_full, sym_full)

            if period_cols:
                # 周期候选值
                period_vals = (norm_p, period.lower(), period.upper(), period)
                placeholders = ",".join("?" for _ in period_vals)
                period_cond = " OR ".join([f"{col} IN ({placeholders})" for col in period_cols])
                params = period_vals * len(period_cols) + sym_params
                cur.execute(f"""
                    SELECT * FROM '{table}'
                    WHERE ({period_cond})
                      AND {sym_where}
                    ORDER BY 数据时间 DESC, 时间 DESC, timestamp DESC, rowid DESC
                    LIMIT 1
                """, params)
            else:
                cur.execute(f"""
                    SELECT * FROM '{table}'
                    WHERE {sym_where}
                    ORDER BY 数据时间 DESC, 时间 DESC, timestamp DESC, rowid DESC
                    LIMIT 1
                """, sym_params)
            row = cur.fetchone()
            return dict(row) if row else {}
        except Exception as exc:
            LOGGER.warning("按行读取表 %s 失败: %s", table, exc)
            return {}
        finally:
            conn.close()

    def _load_csv(self, table: str) -> List[Dict[str, str]]:
        # 依次尝试：映射名、去掉 .py、原名、原名去掉 .py
        mapped = self._resolve_table(table)
        candidates = [
            mapped,
            mapped.replace(".py", ""),
            table,
            table.replace(".py", ""),
        ]
        for cand in candidates:
            path = self.csv_root / f"{cand}.csv"
            if not path.exists():
                continue
            try:
                with path.open("r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            except Exception as exc:
                LOGGER.warning("读取 CSV %s 失败: %s", path, exc)
                return []
        return []

    # ---------------- 公共读取 ----------------
    def fetch_base(self, period: str) -> Dict[str, Dict]:
        """按周期取 `基础数据` 最新一条，返回 symbol -> row dict"""
        rows = self._load_table_period("基础数据", period)

        target_period = _normalize_period_value(period)
        latest: Dict[str, Dict] = {}
        for row in rows:
            r = dict(row)
            r_period = _normalize_period_value(str(r.get("周期")))
            if r_period != target_period:
                continue
            sym = str(r.get("交易对", "")).upper()
            ts = str(r.get("数据时间", ""))
            if not sym:
                continue
            if sym not in latest or ts > latest[sym].get("数据时间", ""):
                latest[sym] = r
        return latest

    def fetch_metric(self, table: str, period: str) -> List[Dict]:
        """通用指标表读取，过滤周期后返回 list[dict]"""
        rows = self._load_table_period(table, period)
        target_period = _normalize_period_value(period)
        out: List[Dict] = []
        for row in rows:
            r = dict(row)
            r_period = _normalize_period_value(str(r.get("周期")))
            if r_period != target_period:
                continue
            out.append(r)
        return out

    def fetch_base_row(self, period: str, symbol: str) -> Dict:
        """获取指定周期+币种的基础数据单行。"""
        return self._fetch_single_row("基础数据", period, symbol)

    def fetch_row(
        self,
        table: str,
        period: str,
        symbol: str,
        *,
        symbol_keys: tuple = ("交易对", "币种", "symbol"),
        base_fields: Optional[List[str]] = None,
    ) -> Dict:
        """仅取指定表/周期/币种的一行，并合并基础数据字段。"""
        row = self._fetch_single_row(table, period, symbol)
        if not row:
            return {}
        base = self.fetch_base_row(period, symbol) or {}
        sym = symbol.upper()
        merged = dict(row)
        merged["symbol"] = sym
        merged["price"] = float(base.get("当前价格", row.get("当前价格", 0)) or 0)
        merged["quote_volume"] = float(base.get("成交额", row.get("成交额", 0)) or 0)
        merged["change_percent"] = float(base.get("变化率", 0) or 0)
        merged["updated_at"] = base.get("数据时间") or row.get("数据时间")
        for k in ["振幅", "交易次数", "成交笔数", "主动买入量", "主动卖出量", "主动买额", "主动卖额", "主动买卖比"]:
            if k in base:
                merged[k] = base.get(k)
        if base_fields:
            for bf in base_fields:
                if bf in base:
                    merged[bf] = base.get(bf)
        return merged

    def merge_with_base(
        self,
        table: str,
        period: str,
        symbol_keys: tuple = ("交易对", "币种", "symbol"),
        base_fields: Optional[List[str]] = None,
    ) -> List[Dict]:
        """合并指标表与 `基础数据`，补齐价格/成交额等字段。

        - `base_fields`：可选，指定需要从基础数据透传的字段名列表（使用原始中文列名）。
        """
        metrics = self.fetch_metric(table, period)
        if not metrics:
            return []
        base_map = self.fetch_base(period)
        merged: List[Dict] = []
        for r in metrics:
            sym = ""
            for key in symbol_keys:
                val = r.get(key)
                if val:
                    sym = str(val).upper()
                    break
            if not sym:
                continue
            base = base_map.get(sym, {})
            row = dict(r)
            row["symbol"] = sym
            row["price"] = float(base.get("当前价格", r.get("当前价格", 0)) or 0)
            row["quote_volume"] = float(base.get("成交额", r.get("成交额", 0)) or 0)
            row["change_percent"] = float(base.get("变化率", 0) or 0)
            row["updated_at"] = base.get("数据时间") or r.get("数据时间")

            # 通用基础字段补齐
            for k in ["振幅", "交易次数", "成交笔数", "主动买入量", "主动卖出量", "主动买额", "主动卖额", "主动买卖比"]:
                if k in base:
                    row[k] = base.get(k)

            if base_fields:
                for bf in base_fields:
                    if bf in base:
                        row[bf] = base.get(bf)
            merged.append(row)
        return merged

    # ---------------- 具体业务 ----------------
    def get_volume_rows(self, period: str) -> List[Dict]:
        metric_rows = self.fetch_metric("Volume", period)
        if not metric_rows:
            return []
        base_map = self.fetch_base(period)
        merged: List[Dict] = []
        for r in metric_rows:
            sym = str(r.get("交易对", "")).upper()
            if not sym:
                continue
            base = base_map.get(sym, {})
            merged.append({
                "symbol": sym,
                "quote_volume": float(base.get("成交额", 0) or 0),
                "base_volume": float(r.get("成交量", 0) or base.get("成交量", 0) or 0),
                "last_close": float(base.get("当前价格", 0) or 0),
                "first_close": float(base.get("开盘价", 0) or 0),
                "change_percent": float(base.get("变化率", 0) or 0) * 100 if abs(float(base.get("变化率", 0) or 0)) < 1 else float(base.get("变化率", 0) or 0),
                "ma5_volume": float(r.get("MA5成交量", 0) or 0),
                "ma20_volume": float(r.get("MA20成交量", 0) or 0),
                "updated_at": base.get("数据时间") or r.get("数据时间"),
            })
        return merged

    def get_atr_rows(self, period: str) -> List[Dict]:
        metrics = self.fetch_metric("ATR波幅榜单", period)
        if not metrics:
            return []
        base_map = self.fetch_base(period)
        out: List[Dict] = []
        for r in metrics:
            sym = str(r.get("交易对", r.get("币种", ""))).upper()
            if not sym:
                continue
            base = base_map.get(sym, {})
            out.append({
                "symbol": sym,
                "strength": float(r.get("强度", 0) or 0),
                "atr_pct": float(r.get("ATR百分比", 0) or 0),
                "price": float(base.get("当前价格", r.get("当前价格", 0)) or 0),
                "category": r.get("波动分类") or "-",
                "quote_volume": float(base.get("成交额", 0) or 0),
                "updated_at": (base.get("数据时间") or r.get("数据时间")),
            })
        return out


_PROVIDER: Optional[RankingDataProvider] = None


def get_ranking_provider() -> RankingDataProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = RankingDataProvider()
    return _PROVIDER


__all__ = [
    "RankingDataProvider", 
    "get_ranking_provider", 
    "format_symbol",
]
