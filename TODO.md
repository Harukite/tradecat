# TODO 列表（按难度从低到高，含验收/审计要点）

- [x] 日志轮转与压缩（S）✅  
  - 动作：`config/logrotate.conf` 按天轮转、保留 14 天并 gzip。  
  - 验收：手动触发轮转后新日志继续写入，旧日志被压缩，无错误日志。  
  - 审计：配置路径与实际日志目录匹配；守护脚本轮转后无 stale fd；磁盘占用下降。

- [x] 安全加载 .env + 权限检查（S）✅  
  - 动作：三份 `services/*/scripts/start.sh` 用只读 kv 解析替代 `source .env`；拒绝含 `export`/`$()`/反引号等危险行；启动前检查 `.env` 权限为 600。  
  - 验收：`.env` 中 `ECHO_TEST='$(whoami)'` 不被执行；权限不符时启动失败并提示。  
  - 审计：脚本无 `source .env`；`stat config/.env` 权限符合；负面用例退出码非 0 且日志含原因。

- [x] SYMBOLS_* 正则校验（S）✅  
  - 动作：data-service / trading-service 启动时对 `SYMBOLS_GROUP*`、`SYMBOLS_EXTRA`、`SYMBOLS_EXCLUDE` 校验 `^[A-Z0-9]+USDT$`（先 upper）。  
  - 验收：非法值提示具体键和值并终止；合法样例可启动。  
  - 审计：启动日志/单测显示非法样例被拒；无静默忽略路径。

- [x] 时间戳比较改用 datetime（S）✅  
  - 动作：`services/telegram-service/src/cards/data_provider.py::fetch_metric` 使用 `datetime.fromisoformat` 解析并比较；支持 Z/+00:00/无时区；解析失败 warning 并跳过。  
  - 验收：混合格式输入排序一致，无重复/漏项；日志有解析失败警告（若触发）。  
  - 审计：代码无字符串直接比较；日志存在解析失败警告路径。

- [x] 代理自检与切换（M）✅  
  - 动作：启动时 3s 内用当前代理 `curl https://api.binance.com/api/v3/ping`；失败清空代理或从 `PROXY_LIST` 选首个可用。  
  - 验收：坏代理场景下日志提示并继续拉数据；好代理场景额外延迟 <1s。  
  - 审计：断网/坏代理测试通过，日志包含代理选择/禁用记录。

- [x] SQLite 连接复用（M）✅  
  - 动作：排行榜读取使用 `_SQLitePool`（3 连接，`check_same_thread=False`），失效自动重建，退出时关闭。  
  - 验收：并发下延迟下降；kill 连接后自动恢复；无 “too many open files”/锁错误。  
  - 审计：代码通过池/单例获取；故障注入后恢复。

- [x] IO/CPU 拆分执行器（M）✅  
  - 动作：新增 `MAX_IO_WORKERS` / `MAX_CPU_WORKERS`，`COMPUTE_BACKEND` 支持 thread/process/hybrid；hybrid：小批(<50)线程，大批进程；避免跨进程大对象。  
  - 验收：CPU 任务多核利用提升、耗时下降；IO 任务不被 GIL 卡。  
  - 审计：调度配置覆盖主要任务；压测无死锁/僵尸进程。

- [x] 批量拉 K 线/批量算指标（M-L）✅
  - 动作：K线读取单SQL批量查询（窗口函数），多周期并行；SQLite写入 `executemany` 批量插入。
  - 验收：吞吐提升，写入速度快 3-5 倍。

- [x] TimescaleDB 压缩策略（M-L）✅
  - 动作：压缩策略改为 30 天后自动压缩；添加 `scripts/timescaledb_compression.sh` 管理脚本。
  - 验收：热数据 30 天不压缩，冷数据自动压缩；不启用自动删除，数据永久保留。
