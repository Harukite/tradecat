# 2026-01-03T04:07:32+08:00 代码审计报告核实
- 任务范围：对用户提供的代码审计摘要逐项与当前仓库源码比对，核实风险点与修复建议。
- 关键发现：
  - 启动脚本 `services/*/scripts/start.sh` 均直接 `source config/.env`，存在环境变量注入风险。
  - `telegram-service/src/signals/` 目录已存在且全局未发现 `from signal` 旧引用，重命名兼容性风险低。
  - `telegram-service/src/cards/data_provider.py` 的最新时间戳去重逻辑使用字符串比较，存在格式差异导致排序错误的潜在风险。
  - 币种白名单读取未做格式校验，仍可能被注入非法符号。
  - data-service 默认代理端口在代码中硬编码为 `http://127.0.0.1:9910`，缺少可用性检测或配置化验证。
- 涉及文件：
  - services/data-service/scripts/start.sh
  - services/trading-service/scripts/start.sh
  - services/telegram-service/scripts/start.sh
  - services/telegram-service/src/cards/data_provider.py
  - services/data-service/src/config.py
- 验证：未执行自动化测试，仅通过源码静态审阅与 `rg` 搜索确认。
- 遗留/下一步：
  - 将 `.env` 加载改为安全解析（例如 `set -a; export $(grep -v '^#' .env | xargs -d '\n'); set +a` 或使用 `python -m dotenv`），并添加用例验证。
  - 为 SYMBOLS_* 配置添加正则校验及单测；将时间戳比较改为 datetime 对象。
  - 评估代理端口配置化与健康检查需求。

# 2026-01-03T04:12:00+08:00 新增待办清单
- 任务范围：整理性能/成本优化方向的详细 TODO。
- 关键内容：新增 `TODO.md`，覆盖 .env 安全加载、代理自检、批量拉取/计算、执行器拆分、SQLite 连接池、时间戳比较、符号校验、Timescale 压缩、日志轮转等项目，按难度排序。
- 涉及文件：
  - TODO.md: 新增待办列表
- 验证：仅文档更新，未改动业务代码。
- 遗留/下一步：按优先级推进 TODO 执行，落地后补充测试与文档。
