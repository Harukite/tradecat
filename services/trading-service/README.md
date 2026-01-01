# Trading Service

指标计算服务，从 TimescaleDB 读取 K 线数据，计算 39 个技术指标，写入 SQLite (market_data.db)。

## 功能

- **39 个技术指标** - MACD、KDJ、RSI、布林带、VPVR、期货情绪等
- **高优先级识别** - 自动识别交易活跃币种优先计算
- **多周期支持** - 1m/5m/15m/1h/4h/1d/1w
- **并行计算** - 多线程/多进程可选

## 目录结构

```
src/
├── core/                    # 计算引擎
│   ├── engine.py            # 同步计算引擎
│   ├── async_full_engine.py # 异步计算引擎
│   └── event_engine.py      # 事件驱动引擎
├── db/
│   ├── reader.py            # TimescaleDB 读取 + SQLite 写入
│   └── cache.py             # 数据缓存
├── indicators/
│   ├── base.py              # 指标基类 + 注册表
│   ├── incremental/         # 增量指标 (9个)
│   └── batch/               # 批量指标 (30个)
├── observability/           # 可观测性
├── config.py                # 配置
├── simple_scheduler.py      # 轮询调度器
└── __main__.py              # CLI 入口
```

## 快速开始

### 启动

```bash
# 方式一：启动脚本（推荐）
./scripts/start.sh          # 启动轮询模式
./scripts/start.sh stop     # 停止
./scripts/start.sh status   # 状态

# 方式二：一次性计算
python3 -m src --once

# 方式三：指定参数
python3 -m src --once --symbols BTCUSDT,ETHUSDT --intervals 5m,15m

# 方式四：轮询调度器
python3 src/simple_scheduler.py
```

### 运行模式

| 模式 | 命令 | 说明 |
|------|------|------|
| 一次性 | `--once` | 计算一次后退出，适合 crontab |
| 异步持续 | `--full-async` | 持续运行，自动检测新数据 |
| 事件驱动 | `--event` | 监听 PostgreSQL NOTIFY |
| 轮询 | `simple_scheduler.py` | 每10秒检查新数据 |

## 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql://...@localhost:5433/market_data` | TimescaleDB |
| `INDICATOR_SQLITE_PATH` | `telegram-service/data/market_data.db` | SQLite 输出 |
| `MAX_WORKERS` | `6` | 并行线程数 |
| `COMPUTE_BACKEND` | `thread` | 计算后端 (thread/process) |
| `KLINE_INTERVALS` | `1m,5m,15m,1h,4h,1d,1w` | K线周期 |
| `FUTURES_INTERVALS` | `5m,15m,1h,4h,1d,1w` | 期货周期 |

### .env.example

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/market_data
INDICATOR_SQLITE_PATH=/path/to/market_data.db
MAX_WORKERS=4
COMPUTE_BACKEND=thread
```

## 指标列表

### 增量指标 (9个)
- 基础数据同步器、MACD柱状扫描器、KDJ随机指标扫描器
- ATR波幅扫描器、G/C点扫描器、OBV能量潮扫描器
- CVD信号排行榜、主动买卖比扫描器、期货情绪元数据

### 批量指标 (30个)
- 布林带、VPVR、VWAP、流动性、MFI资金流量
- K线形态、趋势线、支撑阻力、SuperTrend
- 智能RSI、大资金操盘、量能斐波狙击、零延迟趋势
- 量能信号、多空信号、剥头皮信号、谐波信号
- 期货情绪聚合表、期货缺口监控、数据监控
- ADX、CCI、WilliamsR、Donchian、Keltner、Ichimoku 等

## 数据流

```
TimescaleDB (candles_1m/5m/...)
        │
        ▼
    DataReader (批量读取)
        │
        ▼
    DataCache (内存缓存)
        │
        ▼
    Engine (并行计算)
        │
        ▼
    DataWriter (批量写入)
        │
        ▼
    SQLite (market_data.db)
        │
        ▼
    telegram-service (读取展示)
```

## 输出

写入 `market_data.db`，每个指标一张表：

| 表名 | 说明 |
|------|------|
| `基础数据同步器.py` | 价格、成交量、成交额 |
| `MACD柱状扫描器.py` | MACD、DIF、DEA |
| `期货情绪聚合表.py` | 持仓、多空比、情绪分 |
| ... | 共 39 张表 |
