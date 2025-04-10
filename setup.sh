#!/bin/bash
# ==============================================================================
# Enhanced Kaleidoscope AI Project Setup Script (FORCE Version 6)
#
# Designed to be run WITH sudo. Removes specific logging in find_free_port
# to prevent variable contamination issue. USE WITH CAUTION.
# ==============================================================================

# --- Core Configuration ---
# ... (Same as V4/V5: PROJECT_DIR_NAME, VENV_DIR, etc.) ...
PROJECT_DIR_NAME="kaleidoscope_project_organized"; VENV_DIR=".venv"; PYTHON_CMD=$(command -v python3 || command -v python); MIN_PYTHON_VERSION="3.10"; CONFIG_FILE_NAME="config.json"; REQUIREMENTS_FILE="requirements.txt"; LOG_FILE="setup_log.txt"; FORCE_MODE=true; SETUP_ID=$(date +%s); BACKUP_DIR="setup_backups"

# --- User Detection ---
# ... (Same as V4/V5: Detect ORIGINAL_USER, ORIGINAL_HOME, ORIGINAL_GROUP) ...
ORIGINAL_USER=""; ORIGINAL_HOME=""; ORIGINAL_GROUP="";
if [ "$(id -u)" -eq 0 ]; then # Check if running as root
    if [ -n "$SUDO_USER" ]; then ORIGINAL_USER="$SUDO_USER"; ORIGINAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6); ORIGINAL_GROUP=$(id -gn "$SUDO_USER") || ORIGINAL_GROUP="$SUDO_USER"; echo "[INFO] Running with sudo. Original user: $ORIGINAL_USER (Home: $ORIGINAL_HOME)";
    else echo "[ERROR] Running as root, but cannot determine original user via SUDO_USER."; exit 1; fi
else echo "[ERROR] This script (setup_forced_v6.sh) must be run WITH 'sudo'."; exit 1; fi

# --- Default Tool Paths ---
# ... (Same as V4/V5: Use ORIGINAL_HOME for paths) ...
LLAMA_CPP_BUILD_DIR="$ORIGINAL_HOME/.cache/unravel-ai/build/llama.cpp/build/bin"; LOCAL_BIN_DIR="$ORIGINAL_HOME/.local/bin"; RADARE2_CMD=$(command -v r2 || echo "r2"); GHIDRA_PATH=""; RETDEC_CMD=$(command -v retdec-decompiler || echo "retdec-decompiler"); JSBEAUTIFY_CMD=$(command -v js-beautify || echo "js-beautify"); OLLAMA_CMD=$(command -v ollama || echo "ollama"); LLAMA_SERVER_CMD="llama-server"

# --- Default Configuration Values ---
# ... (Same as V4/V5: Use ORIGINAL_HOME for paths) ...
LLM_DEFAULT_CACHE_DIR="$ORIGINAL_HOME/.cache/unravel-ai/models"; LLM_DEFAULT_MODEL_SUBPATH="TheBloke_Mistral-7B-Instruct-v0.2-GGUF/mistral-7b-instruct-v0.2.Q4_K_M.gguf"; LLM_MODEL_PATH="$LLM_DEFAULT_CACHE_DIR/$LLM_DEFAULT_MODEL_SUBPATH"; LLM_API_BASE="http://localhost:8081"; LLM_PROVIDER="llamacpp_api"; OLLAMA_DEFAULT_MODEL="codellama"; QUANTUM_SYNC_URL="ws://localhost:8765"; WEB_PORT=5000; API_PORT=8000; VIS_PORT=8081; GPU_SUPPORT=false

# --- Command Line Arguments ---
VERBOSE=false; while [[ $# -gt 0 ]]; do case $1 in --verbose|-v) VERBOSE=true; shift ;; *) echo "Unknown option: $1"; exit 1 ;; esac; done

# --- Helper Functions ---
# ... (Same log, log_*, error_exit, success_exit, command_exists from V4/V5) ...
log() { local level="$1"; local message="$2"; local timestamp=$(date "+%Y-%m-%d %H:%M:%S"); local plain_message="[$timestamp] [$level] $message"; local formatted_message="$plain_message"; echo "$plain_message" >> "$LOG_FILE"; if [ -t 1 ] || [ -t 2 ]; then if [[ "$level" == "DEBUG" && "$VERBOSE" != "true" ]]; then return; fi; case "$level" in "INFO") formatted_message="\033[0;32m$plain_message\033[0m";; "WARN") formatted_message="\033[0;33m$plain_message\033[0m";; "ERROR") formatted_message="\033[0;31m$plain_message\033[0m";; "DEBUG") formatted_message="\033[0;36m$plain_message\033[0m";; esac; if [[ "$level" == "ERROR" || "$level" == "WARN" ]]; then echo -e "$formatted_message" >&2; else echo -e "$formatted_message"; fi; fi; }
log_info() { log "INFO" "$1"; }; log_warning() { log "WARN" "$1"; }; log_error() { log "ERROR" "$1"; }; log_debug() { log "DEBUG" "$1"; }
error_exit() { log_error "$1"; log_error "Setup failed. Review '$LOG_FILE'."; exit 1; }
success_exit() { log_info "Installation attempt finished."; log_info "Resetting ownership to $ORIGINAL_USER:$ORIGINAL_GROUP."; log_info "Attempting chown project: $PROJECT_FULL_PATH"; chown -R "$ORIGINAL_USER:$ORIGINAL_GROUP" "$PROJECT_FULL_PATH" || log_warning "Failed chown project dir."; log_info "Attempting chown cache: $LLM_DEFAULT_CACHE_DIR"; mkdir -p "$(dirname "$LLM_DEFAULT_CACHE_DIR")"; chown -R "$ORIGINAL_USER:$ORIGINAL_GROUP" "$(dirname "$LLM_DEFAULT_CACHE_DIR")" || log_warning "Failed chown parent cache."; if [ -d "$LLM_DEFAULT_CACHE_DIR" ]; then chown -R "$ORIGINAL_USER:$ORIGINAL_GROUP" "$LLM_DEFAULT_CACHE_DIR" || log_warning "Failed chown models dir."; fi; log_info "===================================================================="; log_info "Setup summary (forced mode):"; log_info "- Project: $PROJECT_FULL_PATH (Owner: $ORIGINAL_USER)"; log_info "- Venv: $(realpath "$VENV_DIR" 2>/dev/null || echo "$VENV_DIR")"; log_info "- Config: $CONFIG_FILE (Check contents!)"; log_info "- Log: $(realpath "$LOG_FILE")"; log_info "- Web Port: $WEB_PORT"; log_info "- API Port: $API_PORT"; log_info "- Vis Port: $VIS_PORT"; log_info "- LLM Port: $LLM_PORT"; log_info "- Quantum Port: $QUANTUM_PORT"; log_info "===================================================================="; log_info "To run (as '$ORIGINAL_USER' in NEW terminal):"; log_info "1. cd $PROJECT_FULL_PATH"; log_info "2. source $VENV_DIR/bin/activate"; log_info "3. python main.py OR ./start_kaleidoscope.sh"; log_info "===================================================================="; create_startup_script || log_warning "Could not create startup script."; exit 0; }
command_exists() { command -v "$1" &> /dev/null; }

auto_detect_tools() { log_info "Auto-detecting tools..."; # V4 logic
 }
check_python_version() { log_info "Checking Python..."; # V4 logic
 }
is_port_free() { # V4 logic
    local PORT_NUM=$1; local tool_used=""; local grep_pattern="[:.]${PORT_NUM}[[:space:]]";
    if command_exists ss; then ss -tuln | grep -qE "$grep_pattern" && return 1; tool_used="ss";
    elif command_exists netstat; then netstat -tuln | grep -qE "$grep_pattern" && return 1; tool_used="netstat";
    elif command_exists lsof; then lsof -i ":$PORT_NUM" -sTCP:LISTEN -P -n &> /dev/null && return 1; tool_used="lsof";
    else log_warning "Cannot check port $PORT_NUM..." >&2; return 0; fi
    log_debug "Port $PORT_NUM appears free (checked with $tool_used)." >&2 # Ensure debug goes to stderr
    return 0;
}

# FIX V6: Removed specific log_info lines that announce the result to stdout
find_free_port() {
    local START_PORT=$1
    local DESCRIPTION=$2
    local PORT=$START_PORT
    local output_port=""

    while true; do
        # Run check, redirect its potential stdout (debug logs) to stderr
        if is_port_free "$PORT" >&2; then
            # Port is free
            output_port=$PORT
            # --- LOGGING REMOVED --- #
            # No longer printing "Port X is free" or "Resolved conflict..." here
            # ---                --- #
            break # Exit loop, port found
        fi

        # Port is not free, log warning (log function sends to stderr)
        local PROCESS_INFO=""
         if command_exists lsof; then
             PROCESS_INFO=$(lsof -i ":$PORT" -sTCP:LISTEN -n -P -t -F pcn 2>/dev/null | sed -n 's/^p//p; s/^c//p' | paste -sd ' ' -)
         fi
         if [ -n "$PROCESS_INFO" ]; then log_warning "Port $PORT ($DESCRIPTION) is in use by process: $PROCESS_INFO"; else log_warning "Port $PORT ($DESCRIPTION) is in use (process details unavailable)."; fi # Log func handles stderr

        # Force mode kill logic (redirect outputs)
        if [ "$FORCE_MODE" = true ]; then
             local PID=$(echo "$PROCESS_INFO" | grep -oE '^[0-9]+' || echo "")
             if [ -n "$PID" ]; then
                 log_info "--force mode: Killing process $PID on port $PORT..." >&2
                 if kill -9 "$PID" >/dev/null 2>&1; then
                      log_info "Killed process $PID." >&2
                      sleep 1
                      if is_port_free "$PORT" >&2; then
                           # --- LOGGING REMOVED --- #
                           # log_info "Port $PORT ($DESCRIPTION) is now free after kill." >&2
                           # ---                --- #
                           output_port=$PORT
                           break # Exit loop, port freed
                      else log_warning "Port $PORT still in use after kill attempt. Finding next port..." >&2; fi
                 else log_warning "Failed to kill process $PID. Finding next port..." >&2; fi
             else log_warning "--force mode: Cannot determine PID for port $PORT. Finding next port..." >&2; fi
        fi

        # Increment port number
        PORT=$((PORT + 1))
        if [ "$PORT" -gt 65535 ]; then
            log_error "No free ports available up to 65535 for $DESCRIPTION." >&2 # Log error to stderr
            output_port="" # Ensure empty output on error
            break # Exit loop, error condition
        fi
    done

    # Only echo the final port number (or empty string on error) to STANDARD OUTPUT
    echo "$output_port"
    # Determine exit code based on whether a port was found
    [ -n "$output_port" ]
}


create_backup() { # V4 logic
    local file="$1"; if [ -f "$file" ]; then local backup_path="$BACKUP_DIR/$(basename "$file").bak-$SETUP_ID"; mkdir -p "$BACKUP_DIR"; cp "$file" "$backup_path"; log_debug "Created backup of $file at $backup_path"; fi >&2 # Redirect debug
}
update_config_json() { # V4 logic (Python based)
    local config_file="$1"; local section="$2"; local key="$3"; local new_value="$4"; local value_type="$5";
    create_backup "$config_file"
    local python_script=$(cat << EOF
# ... (Exact same Python script from V3/V4/V5) ...
import json, sys, os
config_path = '$config_file'; section = '$section'; key = '$key'; new_value_str = '$new_value'; value_type_hint = '$value_type'
try:
    actual_value = new_value_str # Determine type
    if value_type_hint == 'number':
        try: actual_value = int(new_value_str)
        except ValueError: actual_value = float(new_value_str) # Add better error handling here if needed
    elif value_type_hint != 'string': # Auto-detect
         try: actual_value = int(new_value_str)
         except ValueError:
             try: actual_value = float(new_value_str)
             except ValueError:
                  if new_value_str.lower() == 'true': actual_value = True
                  elif new_value_str.lower() == 'false': actual_value = False
                  elif new_value_str.lower() == 'null': actual_value = None
                  else: actual_value = new_value_str # Keep as string
    data = {}; # Read existing JSON
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f: data = json.load(f)
        except Exception as e: print(f"Warning: Reading '{config_path}' failed ({e}). Overwriting.", file=sys.stderr); data = {}
    else: print(f"Warning: '{config_path}' not found. Creating.", file=sys.stderr); data = {}
    if section not in data: data[section] = {}; data[section][key] = actual_value # Update
    with open(config_path, 'w') as f: json.dump(data, f, indent=2); f.write('\\n') # Write back
    sys.exit(0) # Success
except Exception as e: print(f"Python error: {e}", file=sys.stderr); sys.exit(1)
EOF
)
    if $PYTHON_CMD -c "$python_script"; then log_info "Updated $config_file: Set $section.$key (Python).";
    else log_error "Failed update $config_file: $section.$KEY=$new_value (Python error)."; return 1; fi
}

check_system_dependencies() { log_info "Checking system deps..."; # V4 logic
}
check_python_packages() { log_info "Checking Python pkgs..."; # V4 logic
}
create_startup_script() { log_info "Creating startup script..."; # V4 logic
 }
check_llm_model() { log_info "Checking LLM model..."; # V4 logic
 }

# --- Main Setup Script ---
START_DIR=$(pwd)
log_info "Starting Enhanced Kaleidoscope AI Setup (FORCED MODE V6)..."

# ... (Directory navigation logic as in V4/V5) ...
if [[ "$(basename "$(pwd)")" == "$PROJECT_DIR_NAME" ]]; then PROJECT_FULL_PATH=$(pwd); cd .. || exit 1; START_DIR=$(pwd); cd "$PROJECT_FULL_PATH" || exit 1;
elif [ ! -d "$PROJECT_DIR_NAME" ]; then echo "[ERROR] Project dir '$PROJECT_DIR_NAME' not found."; exit 1;
else cd "$PROJECT_DIR_NAME" || exit 1; PROJECT_FULL_PATH=$(pwd); fi
CONFIG_FILE="$PROJECT_FULL_PATH/$CONFIG_FILE_NAME"; LOG_FILE="$START_DIR/$LOG_FILE"

echo "Kaleidoscope AI Setup Log (FORCED MODE V6) - $SETUP_ID" > "$LOG_FILE" || { echo "FATAL: Cannot write log file $LOG_FILE"; exit 1; }
log_info "Setup started in $PROJECT_FULL_PATH"
log_warning "RUNNING WITH SUDO. Ownership reset to $ORIGINAL_USER at end."

# 1. Checks (Python, System, Pkgs, Tools, Model)
# ... (Calls as in V4/V5) ...
check_python_version; check_system_dependencies; check_python_packages; auto_detect_tools; check_llm_model

# 2. Venv Setup (forced)
# ... (rm -rf, create venv, activate as in V4/V5) ...
log_info "Setting up venv (as root)..."; rm -rf "$VENV_DIR"; $PYTHON_CMD -m venv "$VENV_DIR" || error_exit "Failed venv create."; source "$VENV_DIR/bin/activate" || error_exit "Failed venv activate."; log_info "Venv activated (as root)."

# 3. Install Dependencies (forced)
# ... (pip installs as in V4/V5) ...
log_info "Installing dependencies (as root)..."; if [ ! -f "$REQUIREMENTS_FILE" ]; then error_exit "'$REQUIREMENTS_FILE' not found."; fi; pip install --upgrade pip setuptools wheel || log_warning "Failed pip upgrade."; pip install -r "$REQUIREMENTS_FILE" || error_exit "Failed install from $REQUIREMENTS_FILE."; log_info "Dependencies installed."

# 4. Generate Config (forced)
# ... (cat > "$CONFIG_FILE" as in V4/V5, ensure paths use final variables) ...
log_info "Generating initial $CONFIG_FILE_NAME (as root)..."
LLM_FINAL_CACHE_DIR=$(dirname "$LLM_MODEL_PATH"); LLM_FINAL_MODEL_FILE=$(basename "$LLM_MODEL_PATH")
TEMP_GPU_SUPPORT_STR="false"; if [ "$GPU_SUPPORT" = true ]; then TEMP_GPU_SUPPORT_STR="true"; fi
cat > "$CONFIG_FILE" << EOF # Overwrite config
{
  "paths": { "model_cache": "$LLM_FINAL_CACHE_DIR", /* other paths */ },
  "llm": { "model_file": "$LLM_FINAL_MODEL_FILE", "model_path": "$LLM_MODEL_PATH", /* other llm */ },
  /* ... (Rest of config structure as in V4/V5) ... */
}
EOF
if [ $? -ne 0 ]; then error_exit "Failed writing initial $CONFIG_FILE_NAME"; fi
log_info "Generated initial $CONFIG_FILE_NAME."

# 5. Resolve/Update Ports (forced, using V6 find_free_port)
log_info "Checking/Resolving port conflicts..."
CURRENT_LLM_PORT=$(echo "$LLM_API_BASE" | grep -oE '[0-9]+$' || echo "8081")
CURRENT_QUANTUM_PORT=$(echo "$QUANTUM_SYNC_URL" | grep -oE '[0-9]+$' || echo "8765")
CURRENT_WEB_PORT=$WEB_PORT; CURRENT_API_PORT=$API_PORT; CURRENT_VIS_PORT=$VIS_PORT

# Use V6 find_free_port - should capture only port number now
WEB_PORT=$(find_free_port "$CURRENT_WEB_PORT" "Web Interface") || error_exit "Failed getting port Web"
API_PORT=$(find_free_port "$CURRENT_API_PORT" "API Server") || error_exit "Failed getting port API"
VIS_PORT=$(find_free_port "$CURRENT_VIS_PORT" "Visualizer") || error_exit "Failed getting port Vis"
QUANTUM_PORT=$(find_free_port "$CURRENT_QUANTUM_PORT" "Quantum Server") || error_exit "Failed getting port Quantum"
LLM_PORT=""; if [ "$LLM_PROVIDER" == "llamacpp_api" ]; then LLM_PORT=$(find_free_port "$CURRENT_LLM_PORT" "Llama API") || error_exit "Failed getting port LLM"; fi

# Update config using Python function (should now get clean port numbers)
log_info "Updating config file with resolved ports..."
update_config_json "$CONFIG_FILE" "web_interface" "port" "$WEB_PORT" "number" || log_warning "Failed config update web port"
update_config_json "$CONFIG_FILE" "server" "port" "$API_PORT" "number" || log_warning "Failed config update server port"
update_config_json "$CONFIG_FILE" "visualizer" "port" "$VIS_PORT" "number" || log_warning "Failed config update vis port"
NEW_QUANTUM_SYNC_URL="ws://localhost:$QUANTUM_PORT"; update_config_json "$CONFIG_FILE" "quantum_sync" "server_url" "$NEW_QUANTUM_SYNC_URL" "string" || log_warning "Failed config update quantum URL"; QUANTUM_SYNC_URL="$NEW_QUANTUM_SYNC_URL"
if [ "$LLM_PROVIDER" == "llamacpp_api" ]; then NEW_LLM_API_BASE="http://localhost:$LLM_PORT"; update_config_json "$CONFIG_FILE" "llm" "api_base" "$NEW_LLM_API_BASE" "string" || log_warning "Failed config update LLM URL"; LLM_API_BASE="$NEW_LLM_API_BASE"; fi
log_info "Config file update attempt finished."

# 6. Install Project (forced)
# ... (pip install -e . as in V4/V5) ...
log_info "Installing project editable (as root)..."; pip install -e . || error_exit "Failed install project."; log_info "Project installed."

# 7. Syntax Check (forced)
# ... (syntax check loop as in V4/V5) ...
log_info "Performing syntax check..."; # ... loop ...

# 8. Finalize (calls success_exit which handles chown)
success_exit
