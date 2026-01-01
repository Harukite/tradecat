2024-12-30T00:40:00+08:00 chore: 建立协作基线与单一真源文档体系
- 关键改动点：创建 docs/index.md 作为唯一入口；新增 CONTRIBUTING.md 协作规则；建立 docs/{requirements,design,decisions/adr,prompts,sessions,retros,changelog} 目录结构；创建 ADR/Prompt/Session/Retro 模板；迁移散落文档到真源目录并留索引；新增 .github/PULL_REQUEST_TEMPLATE.md、.githooks/{pre-commit,commit-msg}、.github/workflows/ci.yml、scripts/verify.sh
- 涉及文件或模块：docs/index.md、CONTRIBUTING.md、docs/requirements/REQ-*.md、docs/design/DESIGN-*.md、docs/decisions/adr/*.md、docs/prompts/0000-template.md、docs/sessions/YYYYMMDD-template.md、docs/retros/YYYYMMDD-template.md、docs/parallel-backlog.md、docs/working-agreement.md、.github/*、.githooks/*、scripts/verify.sh
- 验证方式与结果：./scripts/verify.sh 通过
- 遗留问题与下一步：运行 git config core.hooksPath .githooks 启用钩子；后续按需补充 Prompt 和 Session 记录

2025-12-25T01:20:54+08:00 审计：Avellaneda-Stoikov 策略完整性审计  
- 关键改动点：无代码改动；完成对目标实现与 Hummingbot 源码的静态逐行对比并形成审计报告  
- 涉及文件或模块：services/market-maker-v2/src/strategies/avellaneda_stoikov.py；services/market-maker-v2/src/core/indicators.py；libs/external/hummingbot/hummingbot/strategy/avellaneda_market_making/avellaneda_market_making.pyx；libs/external/hummingbot/hummingbot/strategy/__utils__/trailing_indicators/*  
- 验证方式与结果：手工逐行对比、公式核查、配置项对照；发现多个算法与功能与 Hummingbot 不一致  
- 遗留问题与下一步：需要按审计报告修正 TradingIntensityIndicator、订单生命周期、参数覆盖和最优价差/价差档位计算 TODO
2025-12-25T01:38:00+08:00 修复：对齐 Avellaneda-Stoikov 核心公式与指标实现  
- 关键改动点：修正保留价/最优价差的最小价差与档位缩放；库存比率使用 max_inventory；新增 min_spread_bps/eta 支持；补全 update_price；交易强度指标改为 log 线性拟合 alpha/kappa；成交回调传递真实成交数据；多档价差与数量形状对齐 Hummingbot 逻辑；报价精度提升到 4 位  
- 涉及文件或模块：services/market-maker-v2/src/strategies/avellaneda_stoikov.py；services/market-maker-v2/src/core/indicators.py  
- 验证方式与结果：python3 -m py_compile 两文件通过；静态检查公式与缩放与 Hummingbot 源码对比  
- 遗留问题与下一步：尚未实现完整订单生命周期/刷新容差；TradingIntensity 依赖成交样本，需真实交易流喂数据；待补充 order_refresh/预算约束等流程 TODO
2025-12-25T02:05:00+08:00 增强：接入 cryptofeed WebSocket 行情/成交流并记录依赖  
- 关键改动点：新增 core/feed.py，主循环优先用 WS mid，成交流触发策略 on_trade；requirements.txt 增加 cryptofeed；AGENTS 项目结构更新 market-maker-v2 模块  
- 涉及文件或模块：services/market-maker-v2/src/core/feed.py；services/market-maker-v2/main.py；services/market-maker-v2/requirements.txt；AGENTS.md  
- 验证方式与结果：python3 -m py_compile core/feed.py main.py avellaneda_stoikov.py indicators.py 通过  
- 遗留问题与下一步：需在部署环境安装 cryptofeed 依赖；补充 WS 断流重连与快照校准、下单刷新/预算约束 TODO
2025-12-25T02:25:00+08:00 精简：移除非必要 REST 回退，持仓与行情完全走 WS  
- 关键改动点：main.py 不再回退 REST 获取 mid；Engine 去除 fetch_positions 回退，平仓与持仓仅用用户流缓存；保留 listenKey 必需 REST  
- 涉及文件或模块：services/market-maker-v2/main.py；services/market-maker-v2/src/core/engine.py  
- 验证方式与结果：python3 -m py_compile main.py core/engine.py 通过  
- 遗留问题与下一步：需确保用户私有 WS 断线重连与快照校准；若 WS 未就绪则本轮跳过报价，需在运行监控中提示
2025-12-25T02:35:00+08:00 清理：移除 fapiPrivateGetPositionSideDual 探测，改为配置驱动 hedge_mode  
- 关键改动点：Engine 去除 REST 探测持仓模式；ExchangeConfig 增加 hedge_mode；Engine 接口支持 hedge_mode 传入；main.py 创建 Engine 时传递配置  
- 涉及文件或模块：services/market-maker-v2/src/core/engine.py；services/market-maker-v2/src/core/config.py；services/market-maker-v2/main.py  
- 验证方式与结果：python3 -m py_compile core/engine.py core/config.py main.py 通过  
- 遗留问题与下一步：如需自动检测持仓模式需提供可选开关且默认关闭
2025-12-25T02:45:00+08:00 配置：启用测试网双向持仓模式  
- 关键改动点：config/default.json 将 hedge_mode 设为 true（测试网），其余 API/代理保持不变  
- 涉及文件或模块：services/market-maker-v2/config/default.json  
- 验证方式与结果：配置静态更新，未运行代码；运行时 Engine 将按配置开启 hedge_mode  
- 遗留问题与下一步：主网切换时请确认账户已开启双向持仓，否则需改为 false
2025-12-25T01:56:38+08:00 审计：market-maker-v2 REST 调用合规性复核  
- 关键改动点：无代码改动；完成 REST 关键词扫描与核心文件逐行检查，形成允许/违规清单  
- 涉及文件或模块：services/market-maker-v2/src/core/engine.py；services/market-maker-v2/src/core/user_stream.py；services/market-maker-v2/main.py；services/market-maker-v2/src/core/feed.py  
- 验证方式与结果：rg -n \"fetch_|create_|cancel_|listenKey|/fapi\" services/market-maker-v2；人工检查 engine.py/user_stream.py/main.py/feed.py，确认行情/持仓/订单状态均走 WS  
- 遗留问题与下一步：Engine._detect_hedge_mode 仍调用 fapiPrivateGetPositionSideDual，需改为配置驱动或启动参数，避免非必要 REST；待确认是否新增 hedge_mode 配置字段 TODO
2025-12-25T02:04:34+08:00 复核：移除 hedge_mode REST 探测后剩余 REST 清单确认  
- 关键改动点：无代码改动；复核最新代码，确认仅保留交易指令与 listenKey REST；记录 ccxt 隐式 load_markets 可能触发一次性 REST 元数据拉取风险  
- 涉及文件或模块：services/market-maker-v2/src/core/engine.py；services/market-maker-v2/src/core/user_stream.py；services/market-maker-v2/main.py；services/market-maker-v2/src/core/config.py；services/market-maker-v2/config/default.json  
- 验证方式与结果：rg -n \"fetch_|fapi|http|https://|/api/\" services/market-maker-v2；逐行审阅 engine.py/user_stream.py/main.py/config.py/default.json；未发现新增 REST 读写  
- 遗留问题与下一步：ccxt 首次下单会隐式 load_markets 触发 REST 获取合约元数据，若需彻底禁用需预置市场元数据或使用纯 WS 交易库 TODO
2025-12-25T02:18:27+08:00 审计：WS 全量化与双向持仓闭环复核
- 关键改动点：无代码改动；按照提示词完成 REST 调用全量扫描、双向持仓事件链、A-S 算法对齐性与配置复核，形成报告
- 涉及文件或模块：services/market-maker-v2/main.py；services/market-maker-v2/src/core/engine.py；services/market-maker-v2/src/core/feed.py；services/market-maker-v2/src/core/user_stream.py；services/market-maker-v2/src/strategies/avellaneda_stoikov.py；services/market-maker-v2/config/default.json；services/market-maker-v2/requirements.txt
- 验证方式与结果：rg -n "fetch_|listenKey|create_|cancel_|fapi" services/market-maker-v2；python3 -m py_compile main.py src/core/user_stream.py src/strategies/avellaneda_stoikov.py src/core/engine.py；静态逐行审阅上述文件，未发现新增 REST 回退
- 遗留问题与下一步：ccxt 首次下单 load_markets 仍可能触发一次性 REST 获取市场元数据，如需零 REST 需预置 markets 或改用纯 WS 交易库；WS 断线重连与快照校准需在运行监控中关注 TODO
2025-12-25T02:49:04+08:00 文档：同步 README.md 与 AGENTS.md 到现有 market-maker-v2 状态
- 关键改动点：重写项目级 README/AGENTS，聚焦 market-maker-v2，列出真实目录、配置字段、运行/审计命令与 REST 约束；保留零 REST 风险提示
- 涉及文件或模块：README.md；AGENTS.md
- 验证方式与结果：手工比对仓库文件结构、config/default.json、requirements.txt、核心源码；未运行程序
- 遗留问题与下一步：如需彻底禁止 ccxt load_markets REST 需预置市场元数据或替换交易库 TODO
2025-12-25T03:15:00+08:00 稳健性增强：新增零 REST 开关、持仓/行情容错、挂单刷新与风险输入扩展
- 关键改动点：Config 增加 strict_no_rest_markets/markets_path/use_rest_snapshot/account_stale_seconds 及 mid_none_limit/order_ttl/order_price_deviation；Engine 预置 markets 以禁用 load_markets，记录挂单并支持 TTL/偏离撤单；UserStream 增加启动快照可选、ACCOUNT_UPDATE 超时检测；主循环 mid 缺失暂停报价、账户流陈旧暂停下单，风控名义包含挂单；更新 README.md、AGENTS.md 说明；更新默认配置字段。
- 涉及文件或模块：services/market-maker-v2/src/core/config.py；engine.py；user_stream.py；risk.py；main.py；config/default.json；README.md；AGENTS.md
- 验证方式与结果：python3 -m py_compile main.py src/core/user_stream.py src/strategies/avellaneda_stoikov.py src/core/engine.py src/core/config.py src/core/risk.py 通过；rg -n \"fetch_|listenKey|create_|cancel_|fapi\" 无新增违规 REST
- 遗留问题与下一步：strict_no_rest_markets 需要准备 config/markets.json；use_rest_snapshot 调用 REST 会打破零 REST，可按需开启；风险未覆盖实际订单刷新限频，待压测
2025-12-25T03:41:44+08:00 零 REST 落地与风控日志细化
- 关键改动点：生成 config/markets.json 预置 USDM 测试网元数据，默认 strict_no_rest_markets=true 并启动时校验覆盖；Engine 预置 markets_by_id/symbols 禁用 load_markets REST；新增撤单最小间隔配置 cancel_cooldown_seconds 与风控详情日志；main 风控日志补充持仓/挂单/中间价；README/AGENTS 同步配置与文件清单。
- 涉及文件或模块：services/market-maker-v2/config/markets.json；services/market-maker-v2/config/default.json；services/market-maker-v2/src/core/engine.py；services/market-maker-v2/src/core/config.py；services/market-maker-v2/src/core/risk.py；services/market-maker-v2/main.py；services/market-maker-v2/README.md；AGENTS.md
- 验证方式与结果：cd services/market-maker-v2 && python3 -m py_compile main.py src/core/engine.py src/core/config.py src/core/risk.py src/core/user_stream.py src/strategies/avellaneda_stoikov.py 通过；未新增 REST 关键词（代码审阅）。
- 遗留问题与下一步：markets.json 需在新增交易对或合约规格变更时更新；如需启动快照或放开 strict_no_rest_markets 可调 config；撤单限频默认 0.2s，需实盘压测交易所限频。
2025-12-25T03:53:36+08:00 修复：移除默认密钥并修正平仓循环
- 关键改动点：默认配置将 api_key/api_secret 改为占位符；Engine.flat_position 将逐方向平仓并返回成功状态；主循环与退出清理使用新返回值避免本地仓位与实盘不一致；README 增加密钥占位说明。
- 涉及文件或模块：services/market-maker-v2/config/default.json；services/market-maker-v2/src/core/engine.py；services/market-maker-v2/main.py；README.md
- 验证方式与结果：cd services/market-maker-v2 && python3 -m py_compile main.py src/core/user_stream.py src/strategies/avellaneda_stoikov.py src/core/engine.py src/core/config.py src/core/risk.py 通过。
- 遗留问题与下一步：markets.json 完整性校验与生成流程待补；平仓失败时依赖用户流校准仍可能留存风险，后续可返回详细结果并记录告警。
2025-12-25T04:38:26+08:00 稳健性：markets.json 字段校验与快照 REST 告警
- 关键改动点：Engine.validate_markets 增加 precision/limits 关键值检查，防止空值导致下单精度错误；UserStream.start 在 use_rest_snapshot=true 时输出警告提示会触发一次 REST 快照。
- 涉及文件或模块：services/market-maker-v2/src/core/engine.py；services/market-maker-v2/src/core/user_stream.py
- 验证方式与结果：cd services/market-maker-v2 && python3 -m py_compile main.py src/core/user_stream.py src/strategies/avellaneda_stoikov.py src/core/engine.py src/core/config.py src/core/risk.py 通过。
- 遗留问题与下一步：markets.json 仍缺少哈希/更新脚本；use_rest_snapshot 默认关闭但仍需在文档中强调零 REST 场景禁用。
2025-12-25T05:15:47+08:00 加固：markets.json 哈希校验、平仓重试、依赖锁文件
- 关键改动点：Engine 支持 markets.sha256 校验并在 strict_no_rest_markets 时校验失败即退出；新增平仓重试与失败计数；cancel_all 统计限频；Risk 日志目录权限收紧；新增 scripts/gen_markets_sha.py、requirements.lock；Config/README/AGENTS 更新对应字段。
- 涉及文件或模块：services/market-maker-v2/src/core/engine.py；src/core/config.py；src/core/risk.py；main.py；config/default.json；config/markets.sha256；scripts/gen_markets_sha.py；requirements.lock；README.md；AGENTS.md
- 验证方式与结果：cd services/market-maker-v2 && python3 -m py_compile main.py src/core/user_stream.py src/strategies/avellaneda_stoikov.py src/core/engine.py src/core/config.py src/core/risk.py 通过。
- 遗留问题与下一步：markets.json 更新仍需人工或脚本生成真实数据；平仓失败仅重试+日志，缺少外部告警与单元测试；撤单限频/挂单刷新仍需压测；依赖锁版本需确认实际可用版本并定期刷新。
