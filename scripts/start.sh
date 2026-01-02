#!/usr/bin/env bash
# tradecat Pro 统一启动/守护脚本
# 用法: ./scripts/start.sh {start|stop|status|daemon}

set -uo pipefail

# ==================== 配置 ====================
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DAEMON_PID="$ROOT/run/daemon.pid"
DAEMON_LOG="$ROOT/logs/daemon.log"
CHECK_INTERVAL="${CHECK_INTERVAL:-30}"
STOP_TIMEOUT=10

SERVICES=(data-service trading-service telegram-service)

# ==================== 工具函数 ====================
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$DAEMON_LOG"; }

init_dirs() { mkdir -p "$ROOT/run" "$ROOT/logs"; }

read_pid() { [ -f "$1" ] && cat "$1" || echo ""; }

is_running() { [ -n "$1" ] && kill -0 "$1" 2>/dev/null; }

get_uptime() {
    local pid="$1"
    if is_running "$pid"; then
        local start=$(ps -o lstart= -p "$pid" 2>/dev/null)
        [ -n "$start" ] && {
            local diff=$(( $(date +%s) - $(date -d "$start" +%s) ))
            printf "%dd %dh %dm" $((diff/86400)) $((diff%86400/3600)) $((diff%3600/60))
        }
    fi
}

# ==================== 服务控制 ====================
start_service() {
    local svc="$1"
    cd "$ROOT/services/$svc"
    ./scripts/start.sh start 2>&1 | sed "s/^/  [$svc] /"
}

stop_service() {
    local svc="$1"
    cd "$ROOT/services/$svc"
    ./scripts/start.sh stop 2>&1 | sed "s/^/  [$svc] /"
}

status_service() {
    local svc="$1"
    cd "$ROOT/services/$svc"
    ./scripts/start.sh status 2>&1 | head -5 | sed "s/^/  [$svc] /"
}

# ==================== 批量操作 ====================
start_all() {
    echo "=== 启动全部服务 ==="
    for svc in "${SERVICES[@]}"; do
        start_service "$svc"
    done
}

stop_all() {
    echo "=== 停止全部服务 ==="
    for svc in "${SERVICES[@]}"; do
        stop_service "$svc"
    done
}

status_all() {
    echo "=== 服务状态 ==="
    for svc in "${SERVICES[@]}"; do
        status_service "$svc"
        echo ""
    done
}

# ==================== 守护进程 ====================
check_service() {
    local svc="$1"
    local svc_dir="$ROOT/services/$svc"
    
    cd "$svc_dir"
    
    # 检查各服务的 PID 文件
    case "$svc" in
        data-service)
            for name in backfill metrics ws; do
                local pid=$(read_pid "pids/${name}.pid")
                if ! is_running "$pid"; then
                    log "RESTART $svc/$name"
                    ./scripts/start.sh "$name" > /dev/null 2>&1
                fi
            done
            ;;
        trading-service)
            local pid=$(read_pid "pids/service.pid")
            if ! is_running "$pid"; then
                log "RESTART $svc"
                ./scripts/start.sh start > /dev/null 2>&1
            fi
            ;;
        telegram-service)
            local pid=$(read_pid "pids/bot.pid")
            if ! is_running "$pid"; then
                log "RESTART $svc"
                ./scripts/start.sh start > /dev/null 2>&1
            fi
            ;;
    esac
}

monitor_loop() {
    log "=== 守护进程启动 (间隔: ${CHECK_INTERVAL}s) ==="
    while true; do
        for svc in "${SERVICES[@]}"; do
            check_service "$svc"
        done
        sleep "$CHECK_INTERVAL"
    done
}

daemon_start() {
    init_dirs
    local pid=$(read_pid "$DAEMON_PID")
    if is_running "$pid"; then
        echo "守护进程已运行 (PID: $pid)"
        return 0
    fi
    
    start_all
    
    nohup "$0" _monitor >> "$DAEMON_LOG" 2>&1 &
    echo $! > "$DAEMON_PID"
    echo "守护进程已启动 (PID: $!)"
}

daemon_stop() {
    local pid=$(read_pid "$DAEMON_PID")
    if is_running "$pid"; then
        kill -TERM "$pid" 2>/dev/null
        rm -f "$DAEMON_PID"
        log "STOP 守护进程"
        echo "守护进程已停止"
    else
        echo "守护进程未运行"
    fi
    stop_all
}

daemon_status() {
    local pid=$(read_pid "$DAEMON_PID")
    if is_running "$pid"; then
        local uptime=$(get_uptime "$pid")
        echo "守护进程: ✓ 运行中 (PID: $pid, 运行: $uptime)"
    else
        [ -f "$DAEMON_PID" ] && rm -f "$DAEMON_PID"
        echo "守护进程: ✗ 未运行"
    fi
    echo ""
    status_all
}

# ==================== 入口 ====================
init_dirs
cd "$ROOT"

case "${1:-help}" in
    start)    start_all ;;
    stop)     stop_all ;;
    status)   status_all ;;
    restart)  stop_all; sleep 2; start_all ;;
    daemon)   daemon_start ;;
    daemon-stop) daemon_stop ;;
    daemon-status) daemon_status ;;
    _monitor) monitor_loop ;;
    *)
        echo "tradecat Pro 统一启动脚本"
        echo ""
        echo "用法: $0 {start|stop|status|restart|daemon|daemon-stop|daemon-status}"
        echo ""
        echo "  start         启动全部服务"
        echo "  stop          停止全部服务"
        echo "  status        查看状态"
        echo "  restart       重启全部"
        echo "  daemon        启动 + 守护（自动重启挂掉的服务）"
        echo "  daemon-stop   停止守护 + 全部服务"
        echo "  daemon-status 查看守护进程和服务状态"
        exit 1
        ;;
esac
