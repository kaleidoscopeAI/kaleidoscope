#!/bin/bash
# Kaleidoscope AI Startup Script (v3.8 - Fixed llama path, web command, quantum import)
# Generated on $(date)
# Usage: $0 [--stop | --help | --check]

# --- Configuration ---
PROJECT_DIR="/home/jg/Music/include/kaleidoscope_project_organized"
VENV_DIR="${PROJECT_DIR}/.venv"
CONFIG_FILE="${PROJECT_DIR}/config.json"
LOG_DIR="${PROJECT_DIR}/logs"
PID_FILE="${PROJECT_DIR}/kaleidoscope.pids"

# Service settings (Defaults, loaded/checked later)
DEFAULT_LLM_PROVIDER="llamacpp_api"
DEFAULT_LLM_MODEL_PATH="/home/jg/.cache/unravel-ai/models/TheBloke_Mistral-7B-Instruct-v0.2-GGUF/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
DEFAULT_LLM_PORT="8081"
DEFAULT_WEB_PORT="5000"
DEFAULT_API_PORT="8000"
DEFAULT_VIS_PORT="8081"
DEFAULT_QUANTUM_PORT="8765"
# Use a variable that WILL be updated by auto_detect_tools
DETECTED_LLAMA_SERVER_CMD="/home/jg/.local/bin/llama-server" # Start with known good path

# Session identifier
SESSION_NAME="kaleidoscope_$(date +%s)"

# --- Utility Functions ---
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_DIR}/startup.log"
}
error_exit() {
    log "[Error] $1"
    exit 1
}
check_dependency() {
    command -v "$1" &>/dev/null || error_exit "$1 is required but not installed."
}
check_python_dependency() {
    local module=$1
    if [[ -z "$VIRTUAL_ENV" ]] && [ -f "${VENV_DIR}/bin/activate" ]; then
         source "${VENV_DIR}/bin/activate"
    fi
    python3 -c "import $module" 2>/dev/null || error_exit "Python module '$module' is required but not installed in venv ${VENV_DIR}. Run 'pip install $module'."
}
is_port_free() {
    local port=$1
    # Check common tools for checking ports
    if command -v ss &>/dev/null; then
         ss -tuln | grep -q ":$port " && return 1 # Port is busy
    elif command -v lsof &>/dev/null; then
         lsof -i TCP:"$port" -sTCP:LISTEN -n -P >/dev/null 2>&1 && return 1 # Port is busy
    elif command -v netstat &>/dev/null; then
         netstat -tuln | grep -q ":$port " && return 1 # Port is busy
    else
         log "[Warning] Cannot check port $port - 'ss', 'lsof', or 'netstat' not found. Assuming free."
         return 0
    fi
    return 0 # Port is free
}
# Removed find_free_port and assign_port for simplicity, using fixed ports now. Add back if needed.

check_service() {
    local name=$1
    local port=$2
    local retries=15
    local delay=5
    log "Checking status of $name on port $port..."
    for ((i=1; i<=retries; i++)); do
        if ! is_port_free "$port" ; then # Check if port is NOT free (i.e., something is listening)
            log "$name appears to be running on port $port."
            return 0
        fi
        log "Waiting for $name to start ($i/$retries)..."
        sleep $delay
    done
    log "[Warning] $name failed to start/be detected on port $port after $((retries * delay)) seconds."
    return 1
}
load_config_value() {
     local json_path=$1
     local default_value=$2
     if [ ! -f "$CONFIG_FILE" ]; then echo "$default_value"; return; fi
     if command -v jq &>/dev/null ; then
          jq -r "$json_path // \"$default_value\"" "$CONFIG_FILE" || echo "$default_value"
     elif command -v python3 &>/dev/null; then
          $PYTHON_CMD -c "import json; import sys; d=json.load(open('$CONFIG_FILE')); keys='$json_path'.split('.'); v=d; found=True;
try:
  for k in keys[1:]: v=v[k]
except: found=False;
print(v if found and v is not None else '$default_value')" 2>/dev/null || echo "$default_value"
     else
          echo "$default_value"
     fi
}

# --- Setup Environment ---
log "Initializing Kaleidoscope AI Startup"
mkdir -p "$LOG_DIR" || error_exit "Failed to create log directory: $LOG_DIR"

# Validate paths
[ -d "$PROJECT_DIR" ] || error_exit "Project directory not found: $PROJECT_DIR"
[ -f "${VENV_DIR}/bin/activate" ] || error_exit "Virtual environment not found: ${VENV_DIR}/bin/activate"
[ -f "$CONFIG_FILE" ] || error_exit "Configuration file not found: $CONFIG_FILE"

# Load config values needed for checks/startup
FINAL_LLM_PROVIDER=$(load_config_value '.llm.provider' "$DEFAULT_LLM_PROVIDER")
FINAL_LLM_MODEL_PATH=$(load_config_value '.llm.model_path' "$DEFAULT_LLM_MODEL_PATH")
FINAL_LLM_API_BASE=$(load_config_value '.llm.api_base' "http://localhost:$DEFAULT_LLM_PORT") # Use default port
FINAL_LLM_PORT="${FINAL_LLM_API_BASE##*:}" # Extract port from loaded config or default
FINAL_QUANTUM_URL=$(load_config_value '.quantum_sync.server_url' "ws://localhost:$DEFAULT_QUANTUM_PORT")
FINAL_QUANTUM_PORT="${FINAL_QUANTUM_URL##*:}"
FINAL_WEB_PORT=$(load_config_value '.web_interface.port' "$DEFAULT_WEB_PORT")

log "LLM Provider: $FINAL_LLM_PROVIDER"
log "Web Port: $FINAL_WEB_PORT"
log "Quantum Port: $FINAL_QUANTUM_PORT"
if [ "$FINAL_LLM_PROVIDER" == "llamacpp_api" ]; then
    log "LLM Port: $FINAL_LLM_PORT"
    [ -f "$DETECTED_LLAMA_SERVER_CMD" ] || error_exit "LLM server command not found: $DETECTED_LLAMA_SERVER_CMD"
    check_dependency "$DETECTED_LLAMA_SERVER_CMD"
    [ -f "$FINAL_LLM_MODEL_PATH" ] || error_exit "LLM model (for llama.cpp) not found: $FINAL_LLM_MODEL_PATH"
elif [ "$FINAL_LLM_PROVIDER" == "ollama" ]; then
     log "LLM Port (Ollama): $FINAL_LLM_PORT" # Port 11434 assumed
     check_dependency "$OLLAMA_CMD"
fi
[ -f "${PROJECT_DIR}/main.py" ] || error_exit "Main application not found: ${PROJECT_DIR}/main.py"
[ -f "${PROJECT_DIR}/quantum/quantum_server.py" ] || error_exit "Quantum server not found: ${PROJECT_DIR}/quantum/quantum_server.py"


# Check system dependencies
check_dependency python3
check_dependency tmux # Required for this script version

# Activate virtual environment for Python dependency checks
source "${VENV_DIR}/bin/activate" || error_exit "Failed to activate virtual environment"
log "Virtual environment activated"

# Check Python dependencies needed by scripts started here
check_python_dependency websockets # For quantum server
check_python_dependency flask # For main web app
check_python_dependency yaml # For quantum server config loading
# Add others if startup fails due to missing imports

# Check ports before starting
if ! is_port_free "$FINAL_WEB_PORT"; then error_exit "Web UI Port $FINAL_WEB_PORT is already in use."; fi
if ! is_port_free "$FINAL_QUANTUM_PORT"; then error_exit "Quantum Server Port $FINAL_QUANTUM_PORT is already in use."; fi
if [ "$FINAL_LLM_PROVIDER" == "llamacpp_api" ] && ! is_port_free "$FINAL_LLM_PORT"; then error_exit "LLM Server Port $FINAL_LLM_PORT is already in use."; fi
if [ "$FINAL_LLM_PROVIDER" == "ollama" ] && ! is_port_free "$FINAL_LLM_PORT"; then log "[Warning] Ollama Port $FINAL_LLM_PORT seems to be in use - assuming external service is running."; fi


# --- Service Management ---
start_services() {
    log "Starting Kaleidoscope AI Services in $PROJECT_DIR"
    cd "$PROJECT_DIR" || error_exit "Cannot change to project directory"

    log "Starting services in tmux session: $SESSION_NAME"

    # Clean up old sessions first
    EXISTING_SESSION=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep "^kaleidoscope_" | head -n 1)
    if [ -n "$EXISTING_SESSION" ]; then
        log "Terminating existing session: $EXISTING_SESSION"
        tmux kill-session -t "$EXISTING_SESSION" || log "[Warning] Failed to kill session: $EXISTING_SESSION"
        sleep 1
    fi

    # Initialize tmux session
    tmux new-session -d -s "$SESSION_NAME" -n "Main" "echo '--- Kaleidoscope Main App Pane (Window 0) ---'; echo 'Logs will appear here...'; exec bash" || error_exit "Failed to create tmux session"
    log "tmux session created: $SESSION_NAME"

    # Start LLM Service
    LLM_WINDOW_INDEX=1
    if [ "$FINAL_LLM_PROVIDER" == "llamacpp_api" ]; then
        log "Starting LLM Server (llama.cpp) on port $FINAL_LLM_PORT - log: ${LOG_DIR}/llama_server.log"
        tmux new-window -t "$SESSION_NAME" -n "LLM Server" || error_exit "Failed to create LLM Server window"
        # **FIX:** Use the variable containing the full path
        LLAMA_CMD=$(printf "%s -m %s -c 2048 --host 127.0.0.1 --port %s" "$DETECTED_LLAMA_SERVER_CMD" "$FINAL_LLM_MODEL_PATH" "$FINAL_LLM_PORT")
        tmux send-keys -t "${SESSION_NAME}:${LLM_WINDOW_INDEX}" "$LLAMA_CMD > >(tee -a ${LOG_DIR}/llama_server.log) 2>&1" C-m || error_exit "Failed to send LLM Server command"
        tmux send-keys -t "${SESSION_NAME}:${LLM_WINDOW_INDEX}" "echo '[Info] Llama Server running. Ctrl+C in this pane to stop ONLY this server.'" C-m
        if ! check_service "LLM Server" "$FINAL_LLM_PORT"; then
            log "Checking ${LOG_DIR}/llama_server.log for errors..."
            tail -n 15 "${LOG_DIR}/llama_server.log" | while IFS= read -r line; do log "  LLM LOG: $line"; done
            error_exit "LLM Server (llama.cpp) failed to start"
        fi
    elif [ "$FINAL_LLM_PROVIDER" == "ollama" ]; then
        log "Starting LLM Service (Ollama) on port $FINAL_LLM_PORT - log: ${LOG_DIR}/ollama_service.log"
        if is_port_free "$FINAL_LLM_PORT" ; then
            # Attempt to start ollama serve only if port is free
            tmux new-window -t "$SESSION_NAME" -n "LLM Service (Ollama)" || error_exit "Failed to create Ollama Service window"
            OLLAMA_START_CMD="$OLLAMA_CMD serve"
            # Set host/port if needed, depends on ollama version/config
            # Example: OLLAMA_HOST=127.0.0.1:$FINAL_LLM_PORT $OLLAMA_CMD serve
            tmux send-keys -t "${SESSION_NAME}:${LLM_WINDOW_INDEX}" "echo 'Starting Ollama service...'; $OLLAMA_START_CMD > >(tee -a ${LOG_DIR}/ollama_service.log) 2>&1" C-m || error_exit "Failed to send Ollama start command"
            tmux send-keys -t "${SESSION_NAME}:${LLM_WINDOW_INDEX}" "echo '[Info] Ollama service running. Ctrl+C in this pane to stop ONLY this service.'" C-m
            if ! check_service "LLM Service (Ollama)" "$FINAL_LLM_PORT"; then
                log "Checking ${LOG_DIR}/ollama_service.log for errors..."
                tail -n 15 "${LOG_DIR}/ollama_service.log" | while IFS= read -r line; do log "  OLLAMA LOG: $line"; done
                error_exit "LLM Service (Ollama) failed to start"
            fi
        else
             log "[Info] Port $FINAL_LLM_PORT is already in use. Assuming external Ollama service is running."
             # Verify connectivity
             if ! curl -s "http://127.0.0.1:$FINAL_LLM_PORT" >/dev/null 2>&1; then
                  log "[Error] Cannot connect to existing service on port $FINAL_LLM_PORT. Please check your Ollama setup."
                  # Exit here? Or let main app fail? Exiting is safer.
                  error_exit "Cannot connect to required Ollama service."
             else
                  log "[Info] Successfully connected to existing Ollama service on port $FINAL_LLM_PORT."
             fi
             LLM_WINDOW_INDEX=0 # No separate window needed
        fi
    fi

    # Start Quantum Server
    QUANTUM_WINDOW_INDEX=$((LLM_WINDOW_INDEX + 1))
    log "Starting Quantum Server on port $FINAL_QUANTUM_PORT - log: ${LOG_DIR}/quantum_server.log"
    tmux new-window -t "$SESSION_NAME" -n "Quantum Server" || error_exit "Failed to create Quantum Server window"
    tmux send-keys -t "${SESSION_NAME}:${QUANTUM_WINDOW_INDEX}" "cd '$PROJECT_DIR'" C-m # Go to project dir
    tmux send-keys -t "${SESSION_NAME}:${QUANTUM_WINDOW_INDEX}" "source '${VENV_DIR}/bin/activate'" C-m
    # Pass port via argument, redirect output
    tmux send-keys -t "${SESSION_NAME}:${QUANTUM_WINDOW_INDEX}" "python quantum/quantum_server.py --port $FINAL_QUANTUM_PORT > >(tee -a ${LOG_DIR}/quantum_server.log) 2>&1" C-m || error_exit "Failed to send Quantum Server command"
    tmux send-keys -t "${SESSION_NAME}:${QUANTUM_WINDOW_INDEX}" "echo '[Info] Quantum Server running. Ctrl+C in this pane to stop ONLY this server.'" C-m
    if ! check_service "Quantum Server" "$FINAL_QUANTUM_PORT"; then
        log "Checking ${LOG_DIR}/quantum_server.log for errors..."
        tail -n 15 "${LOG_DIR}/quantum_server.log" | while IFS= read -r line; do log "  QUANTUM LOG: $line"; done
        error_exit "Quantum Server failed to start"
    fi

    # Start Web UI
    log "Starting Web UI on port $FINAL_WEB_PORT - log: ${LOG_DIR}/web_app.log"
    tmux select-window -t "${SESSION_NAME}:0" || error_exit "Failed to select Main window"
    tmux select-pane -t "${SESSION_NAME}:0.0" # Ensure first pane
    # **FIX:** Run main.py directly, not the 'kaleidoscope' command
    tmux send-keys -t "${SESSION_NAME}:0.0" "python main.py web --port $FINAL_WEB_PORT > >(tee -a ${LOG_DIR}/web_app.log) 2>&1" C-m || error_exit "Failed to send Web UI command"
    if ! check_service "Web UI" "$FINAL_WEB_PORT"; then
        log "Checking ${LOG_DIR}/web_app.log for errors..."
        tail -n 15 "${LOG_DIR}/web_app.log" | while IFS= read -r line; do log "  WEB LOG: $line"; done
        error_exit "Web UI failed to start"
    fi

    log "-----------------------------------------------------"
    log "Services started successfully in tmux session: $SESSION_NAME"
    log "LLM Service ($FINAL_LLM_PROVIDER): Port $FINAL_LLM_PORT"
    log "Quantum Server: Port $FINAL_QUANTUM_PORT"
    log "Web UI: http://localhost:$FINAL_WEB_PORT"
    log "-----------------------------------------------------"
    log "Attach to session to view logs/output: tmux attach -t $SESSION_NAME"
    log "Detach (leave running): Press Ctrl+b, then d"
    log "Stop everything: $0 --stop"
    log "-----------------------------------------------------"

}

stop_services() {
    log "Stopping Kaleidoscope AI services"
    local session_stopped=0
    local pids_stopped=0

    # Stop tmux session
    SESSION_TO_KILL=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep "^kaleidoscope_" | head -n 1)
    if [ -n "$SESSION_TO_KILL" ]; then
        log "Killing tmux session: $SESSION_TO_KILL"
        if tmux kill-session -t "$SESSION_TO_KILL"; then session_stopped=1; else log "[Warning] Failed to kill tmux session: $SESSION_TO_KILL"; fi
        sleep 1 # Give processes time to exit
    fi

    # Stop background processes using PID file (if it exists)
    if [ -f "$PID_FILE" ]; then
        log "Stopping processes from PID file: $PID_FILE"
        while IFS=: read -r name pid; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                log "Stopping $name (PID: $pid)"
                if kill "$pid"; then pids_stopped=1; else log "[Warning] Failed to kill PID: $pid"; fi
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi

    # Fallback: kill lingering processes if initial methods failed
    if [ "$session_stopped" -eq 0 ] && [ "$pids_stopped" -eq 0 ]; then
         log "Attempting fallback process cleanup..."
         # Make patterns more specific if possible
         pkill -f "$DETECTED_LLAMA_SERVER_CMD.*--port ${FINAL_LLM_PORT}" 2>/dev/null && log "Stopped potential Llama server"
         pkill -f "ollama serve" 2>/dev/null && log "Stopped potential Ollama server"
         pkill -f "python quantum/quantum_server.py --port ${FINAL_QUANTUM_PORT}" 2>/dev/null && log "Stopped potential Quantum server"
         pkill -f "python main.py web --port ${FINAL_WEB_PORT}" 2>/dev/null && log "Stopped potential Web UI"
    fi
    log "Stop command finished."
}

check_status() {
    log "Checking Kaleidoscope AI services status..."
    local running_tmux=0
    local running_ports_summary=""

    SESSION_TO_CHECK=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep "^kaleidoscope_" | head -n 1)
    if [ -n "$SESSION_TO_CHECK" ]; then
        log "[+] tmux session '$SESSION_TO_CHECK' is running."
        running_tmux=1
    else
        log "[-] No active Kaleidoscope tmux session found."
    fi

    PORTS_TO_CHECK=()
    PORTS_DESC=()
    if [ "$FINAL_LLM_PROVIDER" == "llamacpp_api" ]; then PORTS_TO_CHECK+=("$FINAL_LLM_PORT"); PORTS_DESC+=("LLM (llama.cpp)");
    elif [ "$FINAL_LLM_PROVIDER" == "ollama" ]; then PORTS_TO_CHECK+=("$FINAL_LLM_PORT"); PORTS_DESC+=("LLM (Ollama)"); fi
    PORTS_TO_CHECK+=("$FINAL_QUANTUM_PORT" "$FINAL_WEB_PORT")
    PORTS_DESC+=("Quantum Server" "Web UI")

    local any_port_running=0
    for i in "${!PORTS_TO_CHECK[@]}"; do
         port="${PORTS_TO_CHECK[$i]}"
         desc="${PORTS_DESC[$i]}"
         if ! is_port_free "$port"; then
              PROCESS_INFO=$(is_process_running_on_port "$port")
              log "[+] $desc (Port $port) is IN USE by $PROCESS_INFO"
              running_ports_summary+=" $desc(P$port),"
              any_port_running=1
         else
              log "[-] $desc (Port $port) is FREE."
         fi
    done

    if [ "$running_tmux" -eq 1 ] || [ "$any_port_running" -eq 1 ]; then
        log "Summary: Some Kaleidoscope services appear to be running.${running_ports_summary%,}."
    else
        log "Summary: No Kaleidoscope services appear to be running."
    fi
}

# --- Argument Handling ---
case "$1" in
    --help|-h)
        cat << EOF
Kaleidoscope AI Startup Script (v3.8)
Usage: $0 [OPTION]
Options:
  --help, -h      Show this help message
  --stop          Stop all Kaleidoscope services (tmux session and processes)
  --check         Check status of services (ports and tmux session)
  (no option)     Start all services (using tmux if available)
Notes:
  - Reads configuration from $CONFIG_FILE.
  - Logs are stored in $LOG_DIR.
EOF
        exit 0
        ;;
    --stop)
        stop_services
        exit 0
        ;;
    --check)
        check_status
        exit 0
        ;;
    "")
        # Default action: Start services
        # Ensure we are in the project directory first
        cd "$PROJECT_DIR" || error_exit "Cannot change to project directory before starting services"
        start_services
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

exit 0 # Exit successfully after start_services if no option was given
