# TradeCat 优化报告

**日期**: 2026-01-03  
**提交数**: 64 个  
**代码变更**: 63 文件, +1765 行, -2441 行（净减少 676 行）

---

## 一、配置管理统一化

### 1.1 统一配置文件
- 将所有服务的 `.env` 配置合并到 `config/.env` 单文件管理
- 删除各服务私有 `config/` 目录
- 所有服务启动脚本统一加载全局配置

### 1.2 配置文档完善
- `config/.env.example` 添加详细中文注释（201 行）
- 每个配置项包含：用途说明、可选值、获取方式、建议值

### 1.3 环境变量统一
| 变量 | 作用范围 | 说明 |
|---|---|---|
| `SYMBOLS_GROUPS` | 全局 | 控制采集/计算/展示的币种 |
| `HTTP_PROXY` | 全局 | 代理配置，移除所有硬编码 |
| `BOT_TOKEN` | telegram-service | 统一命名 |

---

## 二、代码质量优化

### 2.1 共享模块抽取
创建 `libs/common/symbols.py`，统一币种过滤逻辑：
- `get_configured_symbols()` - 返回列表
- `get_configured_symbols_set()` - 返回集合

三个服务共用，减少约 **102 行**重复代码。

### 2.2 裸 except 修复
全部 `except:` 改为 `except Exception:`，涉及文件：
- data-service: `rate_limiter.py`
- trading-service: `engine.py`, `reader.py`, `liquidity.py` 等
- telegram-service: `app.py`, `non_blocking_ai_handler.py`
- order-service: `risk.py`

### 2.3 硬编码移除
| 类型 | 修复前 | 修复后 |
|---|---|---|
| 代理地址 | `http://127.0.0.1:9910` | 从 `HTTP_PROXY` 读取 |
| 绝对路径 | `/home/lenovo/...` | 相对路径 + `PROJECT_ROOT` |
| 配置路径 | `SERVICE_ROOT/config/.env` | `PROJECT_ROOT/config/.env` |

---

## 三、Bug 修复

### 3.1 资金流向卡片数据问题
**问题**: 显示 488 个旧币种而非当前 6 个高优先级币种

**原因**: 
1. `fetch_base()` 返回所有历史数据，未按最新批次过滤
2. 周期标准化 `{"1d": "24h", "24h": "1d"}` 造成死循环

**修复**:
- `fetch_base()` 只返回最新时间戳的数据
- 添加 `SYMBOLS_GROUPS` 币种过滤
- 修复周期标准化映射

### 3.2 SQLite 连接问题
- 添加连接复用（单例模式）
- 启用 WAL 模式
- 添加 `atexit` 清理钩子

---

## 四、依赖管理

### 4.1 版本锁定
更新 `requirements.lock.txt` 为完整依赖树：
| 服务 | 依赖数 |
|---|---|
| data-service | 33 |
| trading-service | 16 |
| telegram-service | 20 |
| order-service | 30 |

---

## 五、仓库清理

### 5.1 移除跟踪的文件
从 Git 仓库移除（本地保留）：
- `AUDIT_REPORT.md`
- `CODE_LOCATIONS.md`
- `OPTIMIZATION_TODO.md`
- `MARKETING.md`
- `CHANGELOG.md`
- `1`, `3`（临时文件）

### 5.2 目录结构调整
- `install.sh` 移动到 `scripts/` 目录
- 删除各服务 `config/` 目录

---

## 六、文档更新

- `README.md` - 更新目录结构和配置说明
- `AGENTS.md` - 更新配置路径和环境变量参考
- `Makefile` - 添加 `install` 和 `daemon-stop` 命令

---

## 七、最终状态

### 检查项通过
- ✅ 无硬编码代理
- ✅ 无硬编码路径
- ✅ 无裸 except
- ✅ 无服务私有配置引用
- ✅ 配置统一到 `config/.env`
- ✅ 依赖版本锁定

### 服务运行状态
- ✅ telegram-service 正常
- ✅ trading-service 正常（识别 6 币种）
- ✅ data-service metrics 正常

---

## 八、提交历史（关键）

```
39203bb fix(telegram-service): 修复裸 except
06252fa refactor: 移除硬编码代理，统一使用 HTTP_PROXY
ec74448 chore: 更新 requirements.lock.txt 为完整依赖树
e78ebd2 feat(libs): 添加共享币种管理模块
d0c59ad fix: 修复各服务 .env 加载路径指向全局配置
37c6b6f docs: 为 .env.example 添加详细字段注释
d4ad02e refactor: 统一配置管理到 config/.env
732861a fix(telegram): fetch_base 改为只取最新批次数据
f020cf1 perf(trading): SQLite 连接复用
```
