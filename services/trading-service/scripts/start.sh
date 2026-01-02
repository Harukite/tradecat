#!/usr/bin/env bash
# trading-service 启动/守护脚本
# 用法: ./scripts/start.sh {start|stop|status|restart|daemon}

set -uo pipefail

# ==================== 配置区 ====================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$SERVICE_DIR")")"
RUN_DIR="$SERVICE_DIR/pids"
LOG_DIR="$SERVICE_DIR/logs"
DAEMON_PID="$RUN_DIR/daemon.pid"
DAEMON_LOG="$LOG_DIR/daemon.log"
SERVICE_PID="$RUN_DIR/service.pid"
SERVICE_LOG="$LOG_DIR/service.log"
CHECK_INTERVAL="${CHECK_INTERVAL:-30}"
STOP_TIMEOUT=10

# 加载配置（按顺序，后加载覆盖先加载）
load_env() {
    [ -f "$1" ] && { set -a; source "$1"; set +a; }
}
load_env "$PROJECT_ROOT/config/.env.shared"
load_env "$PROJECT_ROOT/config/.env.secrets"
load_env "$SERVICE_DIR/config/.env"

# 启动命令
MODE="${MODE:-simple}"
START_CMD="python3 -u src/simple_scheduler.py"
[ "$MODE" = "listener" ] && START_CMD="python3 -u src/kline_listener.py"

# ==================== 工具函数 ====================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$DAEMON_LOG"
}

init_dirs() {
    mkdir -p "$RUN_DIR" "$LOG_DIR"
}

is_running() {
    local pid=$1
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

get_service_pid() {
    [ -f "$SERVICE_PID" ] && cat "$SERVICE_PID"
}

# ==================== 服务管理 ====================
start_service() {
    init_dirs
    local pid=$(get_service_pid)
    if is_running "$pid"; then
        echo "✓ 服务已运行 (PID: $pid)"
        return 0
    fi
    
    cd "$SERVICE_DIR"
    source .venv/bin/activate
    export PYTHONPATH=src
    nohup $START_CMD >> "$SERVICE_LOG" 2>&1 &
    local new_pid=$!
    echo "$new_pid" > "$SERVICE_PID"
    
    sleep 1
    if is_running "$new_pid"; then
        log "START 服务 (PID: $new_pid, MODE: $MODE)"
        echo "✓ 服务已启动 (PID: $new_pid, MODE: $MODE)"
        return 0
    else
        log "ERROR 服务启动失败"
        echo "✗ 服务启动失败"
        return 1
    fi
}

stop_service() {
    local pid=$(get_service_pid)
    if ! is_running "$pid"; then
        echo "服务未运行"
        rm -f "$SERVICE_PID"
        return 0
    fi
    
    kill "$pid" 2>/dev/null
    local waited=0
    while is_running "$pid" && [ $waited -lt $STOP_TIMEOUT ]; do
        sleep 1
        ((waited++))
    done
    
    if is_running "$pid"; then
        kill -9 "$pid" 2>/dev/null
        log "KILL 服务 (PID: $pid) 强制终止"
    else
        log "STOP 服务 (PID: $pid)"
    fi
    
    rm -f "$SERVICE_PID"
    echo "✓ 服务已停止"
}

status_service() {
    local pid=$(get_service_pid)
    if is_running "$pid"; then
        local uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
        echo "✓ 服务运行中 (PID: $pid, 运行: $uptime)"
        echo ""
        echo "=== 最近日志 ==="
        tail -10 "$SERVICE_LOG" 2>/dev/null
    else
        echo "✗ 服务未运行"
    fi
}

# ==================== 入口 ====================
case "${1:-status}" in
    start)   start_service ;;
    stop)    stop_service ;;
    status)  status_service ;;
    restart) stop_service; sleep 2; start_service ;;
    *)
        echo "用法: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac
