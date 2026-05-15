#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$DIR/app.pid"
LOG_FILE="$DIR/app.log"
PORT=8080

_red()   { printf '\033[31m%s\033[0m\n' "$1"; }
_green() { printf '\033[32m%s\033[0m\n' "$1"; }
_yellow(){ printf '\033[33m%s\033[0m\n' "$1"; }
_info()  { printf '[SVC] %s\n' "$1"; }

_is_alive() {
    local pid="$1"
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

_get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE" 2>/dev/null
    fi
}

_get_port_pids() {
    lsof -ti:$PORT 2>/dev/null || true
}

_status() {
    local pid body port_pids
    pid="$(_get_pid)"
    port_pids="$(_get_port_pids)"

    _info "SERVICE_NAME=yzxnice"
    _info "PORT=$PORT"
    _info "PID_FILE=$PID_FILE"
    _info "LOG_FILE=$LOG_FILE"

    if [ -n "$pid" ] && _is_alive "$pid"; then
        _info "STATE=running"
        _info "PID=$pid"
        _green "STATUS: service is running (pid $pid, port $PORT)"
    else
        _info "STATE=stopped"
        if [ -n "$pid" ]; then
            _info "STALE_PID=$pid (process dead, pid file stale)"
        fi
        if [ -n "$port_pids" ]; then
            _red "STATUS: service stopped, but orphan processes on port $PORT: $(echo $port_pids | tr '\n' ' ')"
        else
            _yellow "STATUS: service is stopped"
        fi
        return 1
    fi
}

_stop() {
    local pid port_pids waited

    pid="$(_get_pid)"
    port_pids="$(_get_port_pids)"

    if [ -z "$pid" ] && [ -z "$port_pids" ]; then
        _green "STATUS: already stopped, nothing to do"
        rm -f "$PID_FILE"
        return 0
    fi

    [ -n "$pid" ] && _info "stopping pid $pid ..."
    [ -n "$port_pids" ] && _info "stopping port $PORT processes: $(echo $port_pids | tr '\n' ' ')"

    for p in $pid $port_pids; do
        kill "$p" 2>/dev/null || true
    done

    waited=0
    while [ $waited -lt 10 ]; do
        port_pids="$(_get_port_pids)"
        pid="$(_get_pid)"
        alive=""
        [ -n "$pid" ] && _is_alive "$pid" && alive=1
        [ -z "$alive" ] && [ -z "$port_pids" ] && break
        sleep 1
        waited=$((waited + 1))
    done

    port_pids="$(_get_port_pids)"
    if [ -n "$port_pids" ]; then
        _info "force killing remaining: $(echo $port_pids | tr '\n' ' ')"
        for p in $port_pids; do
            kill -9 "$p" 2>/dev/null || true
        done
        sleep 1
    fi

    rm -f "$PID_FILE"

    port_pids="$(_get_port_pids)"
    if [ -z "$port_pids" ]; then
        _green "STATUS: service stopped and verified"
    else
        _red "STATUS: failed to stop processes: $(echo $port_pids | tr '\n' ' ')"
        return 1
    fi
}

_start() {
    local pid
    pid="$(_get_pid)"

    if [ -n "$pid" ] && _is_alive "$pid"; then
        _yellow "STATUS: already running (pid $pid, port $PORT)"
        _info "use 'restart' to force restart"
        return 0
    fi

    rm -f "$PID_FILE"

    _info "starting service ..."
    nohup python "$DIR/main.py" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    pid="$(_get_pid)"

    local waited=0
    while [ $waited -lt 15 ]; do
        if _is_alive "$pid" && [ -n "$(_get_port_pids)" ]; then
            _green "STATUS: service started (pid $pid, port $PORT)"
            _info "LOG_TAIL_START:"
            tail -3 "$LOG_FILE" | sed 's/^/  /'
            _info "LOG_TAIL_END"
            return 0
        fi
        if ! _is_alive "$pid"; then
            _red "STATUS: process exited prematurely"
            _info "LOG_TAIL_START:"
            tail -10 "$LOG_FILE" | sed 's/^/  /'
            _info "LOG_TAIL_END"
            return 1
        fi
        sleep 1
        waited=$((waited + 1))
    done

    _red "STATUS: service did not become ready within 15s"
    return 1
}

_restart() {
    _info "=== RESTART ==="
    _stop
    _info "---"
    _start
}

case "${1:-}" in
    start)   _start   ;;
    stop)    _stop    ;;
    restart) _restart ;;
    status)  _status  ;;
    *)
        echo "usage: $0 {start|stop|restart|status}"
        echo ""
        echo "  start   - start service (skip if already running)"
        echo "  stop    - stop service and verify processes are gone"
        echo "  restart - unconditionally stop then start"
        echo "  status  - show service state"
        exit 1
        ;;
esac
