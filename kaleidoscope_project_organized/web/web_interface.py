#!/usr/bin/env python3
"""
Kaleidoscope AI Web Interface (Enhanced Version)
A feature-rich Flask interface for software ingestion and mimicry with advanced task management, authentication, and real-time updates.
"""

import os
import sys
import time
import json
import uuid
import logging
import argparse
import threading
import queue
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path
from flask import (
    Flask, render_template, request, jsonify, send_file, redirect, url_for, Response, session, flash
)
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from flask_socketio import SocketIO, emit
from flask_apscheduler import APScheduler
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman

# Project root setup
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(PROJECT_ROOT))

# Import KaleidoscopeCore
try:
    from core.kaleidoscope_core import KaleidoscopeCore
except ImportError as e:
    print(f"Error: Cannot import KaleidoscopeCore - {e}. Ensure project is installed ('pip install -e .') and venv is active.")
    sys.exit(1)

# Logging Configuration
logger = logging.getLogger("WebInterfaceEnhanced")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(PROJECT_ROOT / "web_interface_enhanced.log")
        ]
    )

# Flask App Setup
app = Flask(
    __name__,
    template_folder=SCRIPT_DIR / "templates",
    static_folder=SCRIPT_DIR / "static"
)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex()),
    MAX_CONTENT_LENGTH=100 * 1024 * 1024,  # 100MB upload limit
    UPLOAD_FOLDER=str(PROJECT_ROOT / "uploads"),
    SESSION_COOKIE_SECURE=True,
    REMEMBER_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_HTTPONLY=True
)

# Security Enhancements
Talisman(app, content_security_policy={
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline'",
    "style-src": "'self' 'unsafe-inline'"
})
csrf = CSRFProtect(app)

# SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Scheduler for task scheduling
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Login Manager for authentication
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# User model (simplified for example)
class User(UserMixin):
    def __init__(self, id: str, username: str):
        self.id = id
        self.username = username

# Simulated user database
users = {
    "user1": User("1", "user1")
}

@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    return users.get(user_id)

# Global State
kaleidoscope: Optional[KaleidoscopeCore] = None
task_queue = queue.Queue()
current_task: Optional[Dict[str, Any]] = None
task_history: List[Dict[str, Any]] = []
worker_thread: Optional[threading.Thread] = None
running = threading.Event()
cancelled_tasks = set()

ALLOWED_EXTENSIONS = {
    'exe', 'dll', 'so', 'dylib', 'bin',
    'js', 'mjs', 'py', 'c', 'cpp', 'h', 'hpp',
    'java', 'class', 'jar', 'go', 'rs',
    'php', 'rb', 'cs', 'asm', 's'
}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Worker Functions
def worker_loop() -> None:
    """Background worker to process tasks."""
    logger.info("Worker thread started")
    running.set()
    while running.is_set():
        try:
            task = task_queue.get(timeout=1.0)
            if task is None or task["id"] in cancelled_tasks:
                continue
            with app.app_context():
                process_task(task)
            task_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            if current_task:
                current_task["status"] = "error"
                current_task["error"] = str(e)
                task_history.append(current_task.copy())
    logger.info("Worker thread stopped")

def process_task(task: Dict[str, Any]) -> None:
    """Process a task."""
    global current_task
    current_task = task
    task["status"] = "processing"
    try:
        if task["type"] == "ingest":
            result = kaleidoscope.ingest_software(task["file_path"])
        elif task["type"] == "mimic":
            result = kaleidoscope.mimic_software([task["spec_path"]], task["target_language"])
        else:
            raise ValueError(f"Unknown task type: {task['type']}")
        task.update(result)
        task["status"] = "completed"
        socketio.emit("task_update", {"task_id": task["id"], "status": "completed"})
    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        socketio.emit("task_update", {"task_id": task["id"], "status": "error", "error": str(e)})
    finally:
        task_history.append(task.copy())
        current_task = None

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login() -> Response:
    """Handle user login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = users.get(username)
        if user and password == "password":  # Simplified password check
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout() -> Response:
    """Handle user logout."""
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))

# Main Routes
@app.route('/')
@login_required
def index() -> str:
    """Render the main page."""
    return render_template("index.html")

@app.route('/upload', methods=['POST'])
@login_required
def upload_file() -> Response:
    """Handle multiple file uploads for ingestion."""
    if not kaleidoscope:
        return jsonify({"error": "System not initialized"}), 503
    if 'files' not in request.files:
        return jsonify({"error": "No files part"}), 400
    files = request.files.getlist('files')
    if not files or any(not f.filename for f in files):
        return jsonify({"error": "No files selected"}), 400
    if any(not allowed_file(f.filename) for f in files):
        return jsonify({"error": "Some files have disallowed types"}), 400
    try:
        task_ids = []
        for file in files:
            filename = secure_filename(file.filename)
            file_path = Path(app.config['UPLOAD_FOLDER']) / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file.save(file_path)
            task_id = str(uuid.uuid4())
            task = {
                "id": task_id,
                "type": "ingest",
                "file_path": str(file_path),
                "original_filename": filename,
                "timestamp": time.time(),
                "status": "pending",
                "user": current_user.username
            }
            task_queue.put(task)
            task_ids.append(task_id)
        return jsonify({"task_ids": task_ids})
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({"error": "Upload failed"}), 500

@app.route('/mimic', methods=['POST'])
@login_required
def mimic_software() -> Response:
    """Handle software mimicry request with scheduling option."""
    if not kaleidoscope:
        return jsonify({"error": "System not initialized"}), 503
    data = request.form
    spec_path = data.get("spec_path")
    target_language = data.get("target_language")
    source_task_id = data.get("source_task_id")
    schedule_time = data.get("schedule_time")  # Optional: ISO format
    if not target_language:
        return jsonify({"error": "Target language required"}), 400
    if source_task_id:
        task = next((t for t in task_history if t["id"] == source_task_id and t["status"] == "completed"), None)
        if not task or "spec_files" not in task or not task["spec_files"]:
            return jsonify({"error": "Valid source task not found"}), 400
        spec_path = task["spec_files"][0]
    elif not spec_path or not Path(spec_path).exists():
        return jsonify({"error": "Valid spec path required"}), 400
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "type": "mimic",
        "spec_path": spec_path,
        "target_language": target_language,
        "source_task_id": source_task_id,
        "timestamp": time.time(),
        "status": "pending",
        "user": current_user.username
    }
    if schedule_time:
        try:
            schedule_dt = datetime.fromisoformat(schedule_time)
            scheduler.add_job(
                func=lambda: task_queue.put(task),
                trigger="date",
                run_date=schedule_dt,
                id=task_id
            )
            task["status"] = "scheduled"
            task["scheduled_time"] = schedule_time
        except ValueError:
            return jsonify({"error": "Invalid schedule time format"}), 400
    else:
        task_queue.put(task)
    return jsonify({"task_id": task_id})

@app.route('/cancel_task/<task_id>', methods=['POST'])
@login_required
def cancel_task(task_id: str) -> Response:
    """Cancel a pending or processing task."""
    global cancelled_tasks
    if task_id in [t["id"] for t in task_queue.queue]:
        cancelled_tasks.add(task_id)
        return jsonify({"message": "Task cancelled"})
    elif current_task and current_task["id"] == task_id:
        cancelled_tasks.add(task_id)
        return jsonify({"message": "Task will be cancelled after current operation"})
    else:
        return jsonify({"error": "Task not found or already completed"}), 404

@app.route('/status')
@login_required
def get_status() -> Response:
    """Return task status with user filtering."""
    user_tasks = [t for t in task_history if t["user"] == current_user.username]
    return jsonify({
        "current_task": current_task if current_task and current_task["user"] == current_user.username else None,
        "tasks": user_tasks
    })

@app.route('/task/<task_id>')
@login_required
def get_task_details(task_id: str) -> Response:
    """Get specific task details."""
    task = current_task if current_task and current_task["id"] == task_id else None
    if not task:
        task = next((t for t in task_history if t["id"] == task_id and t["user"] == current_user.username), None)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    result = task.copy()
    if task["status"] == "completed":
        if task["type"] == "ingest":
            result["links"] = {
                "specs": f"/download/{task_id}/specs",
                "reconstructed": f"/download/{task_id}/reconstructed"
            }
        elif task["type"] == "mimic":
            result["links"] = {"mimicked": f"/download/{task_id}/mimicked"}
    return jsonify(result)

@app.route('/download/<task_id>/<file_type>')
@login_required
def download_results(task_id: str, file_type: str) -> Response:
    """Download task results as ZIP."""
    task = next((t for t in task_history if t["id"] == task_id and t["status"] == "completed" and t["user"] == current_user.username), None)
    if not task:
        return jsonify({"error": "Task not found or not completed"}), 404
    files_key = {
        "ingest": {"specs": "spec_files", "reconstructed": "reconstructed_files"},
        "mimic": {"mimicked": "mimicked_files"}
    }.get(task["type"], {}).get(file_type)
    if not files_key or files_key not in task:
        return jsonify({"error": "Invalid file type"}), 400
    import zipfile
    from io import BytesIO
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in task[files_key]:
            if Path(file_path).exists():
                zipf.write(file_path, Path(file_path).name)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{file_type}_{task_id}.zip",
        mimetype='application/zip'
    )

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings() -> str:
    """Manage LLM settings with enhanced options."""
    config_path = PROJECT_ROOT / "config.json"
    config = {}
    if config_path.exists():
        with config_path.open('r') as f:
            config = json.load(f)
    if request.method == 'POST':
        llm = config.setdefault("llm", {})
        llm["default_model"] = request.form.get("default_model", "mistral-7b-instruct-v0.2")
        llm["temperature"] = float(request.form.get("temperature", 0.2))
        llm["max_tokens"] = int(request.form.get("max_tokens", 2048))
        llm["api_base"] = request.form.get("api_base", "http://127.0.0.1:8081")
        llm["additional_param"] = request.form.get("additional_param", "")  # Example
        with config_path.open('w') as f:
            json.dump(config, f, indent=2)
        return redirect(url_for('settings', message="Settings updated"))
    models = kaleidoscope.list_models() if kaleidoscope else ["mistral-7b-instruct-v0.2"]
    return render_template('settings.html', config=config, available_models=models)

# Error Handlers
@app.errorhandler(HTTPException)
def handle_http_exception(e: HTTPException) -> Response:
    """Handle HTTP errors."""
    return jsonify({"error": e.description}), e.code

@app.errorhandler(Exception)
def handle_uncaught_exception(e: Exception) -> Response:
    """Handle uncaught exceptions."""
    logger.error(f"Uncaught exception: {e}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500

# Server Startup
def start_server(
    work_dir: Optional[str] = None,
    host: str = "127.0.0.1",
    port: int = 5000,
    config_path: Optional[str] = None
) -> None:
    """Start the Flask server with enhanced features."""
    global kaleidoscope, worker_thread
    config_file = Path(config_path or (PROJECT_ROOT / "config.json"))
    config = {}
    if config_file.exists():
        try:
            with config_file.open('r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Config load failed: {e}", exc_info=True)
    work_dir = work_dir or config.get("paths", {}).get("data_dir", str(PROJECT_ROOT / "data"))
    app.config["UPLOAD_FOLDER"] = str(Path(work_dir) / "uploads")
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    llm_endpoint = config.get("llm", {}).get("api_base", "http://127.0.0.1:8081")
    try:
        kaleidoscope = KaleidoscopeCore(
            work_dir=work_dir,
            llm_endpoint=llm_endpoint,
            max_workers=config.get("max_workers", 4)
        )
    except Exception as e:
        logger.critical(f"KaleidoscopeCore init failed: {e}", exc_info=True)
        raise
    if not worker_thread or not worker_thread.is_alive():
        worker_thread = threading.Thread(target=worker_loop, daemon=True)
        worker_thread.start()
    host = host or config.get("web_interface", {}).get("host", "127.0.0.1")
    port = port or config.get("web_interface", {}).get("port", 5000)
    logger.info(f"Starting server on http://{host}:{port}")
    try:
        from waitress import serve  # Production server
        serve(app, host=host, port=port, threads=8)
    except ImportError:
        app.run(host=host, port=port, debug=False, threaded=True)
    except Exception as e:
        logger.critical(f"Server start failed: {e}", exc_info=True)
    finally:
        running.clear()
        if worker_thread and worker_thread.is_alive():
            task_queue.put(None)
            worker_thread.join(timeout=5.0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kaleidoscope AI Web Interface (Enhanced)")
    parser.add_argument("--work-dir", help="Working directory")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=5000, help="Port")
    parser.add_argument("--config", help="Config file path")
    parser.add_argument("--log", default="INFO", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    args = parser.parse_args()
    logging.getLogger().setLevel(args.log.upper())
    try:
        start_server(args.work_dir, args.host, args.port, args.config)
    except Exception as e:
        logger.critical(f"Server failed: {e}", exc_info=True)
        sys.exit(1)late('index.html')@app.route('/upload', methods=['POST'])def upload_file():    """Handle file upload for ingestion"""    # Check if file was uploaded    if 'file' not in request.files:        return jsonify({"error": "No file part"}), 400        file = request.files['file']        # Check if file was selected    if file.filename == '':        return jsonify({"error": "No file selected"}), 400        # Check if file is allowed    if not file and not allowed_file(file.filename):        return jsonify({"error": "File type not allowed"}), 400        # Save the file    filename = secure_filename(file.filename)    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)    file.save(file_path)        # Create ingestion task    task_id = str(uuid.uuid4())    task = {        "id": task_id,        "type": "ingest",        "file_path": file_path,        "original_filename": filename,        "timestamp": time.time(),        "status": "pending"    }        # Add to task history and queue    task_history.append(task)    task_queue.put(task)        return jsonify({"task_id": task_id})@app.route('/mimic', methods=['POST'])def mimic_software():    """Handle request to mimic software"""    # Get parameters    spec_path = request.form.get('spec_path')    target_language = request.form.get('target_language')    source_task_id = request.form.get('source_task_id')        # Validate parameters    if not spec_path and not source_task_id:        return jsonify({"error": "No specification file or source task provided"}), 400        if not target_language:        return jsonify({"error": "No target language specified"}), 400        # If source_task_id is provided, get the spec file from that task    if source_task_id:        source_task = None        for task in task_history:            if task["id"] == source_task_id:                source_task = task                break                if not source_task or source_task["status"] != "completed":            return jsonify({"error": "Source task not found or not completed"}), 400                # Get the first spec file from the source task        if "result" in source_task and "spec_files" in source_task["result"]:            spec_files = source_task["result"]["spec_files"]            if spec_files:                spec_path = spec_files[0]            else:                return jsonify({"error": "No specification files found in source task"}), 400        else:            return jsonify({"error": "No specification files found in source task"}), 400        # Create mimic task    task_id = str(uuid.uuid4())    task = {        "id": task_id,        "type": "mimic",        "spec_path": spec_path,        "target_language": target_language,        "source_task_id": source_task_id,        "timestamp": time.time(),        "status": "pending"    }        # Add to task history and queue    task_history.append(task)    task_queue.put(task)        return jsonify({"task_id": task_id})@app.route('/status')def get_status():    """Get the status of all tasks and the current task"""    # Create response with task history    response = {        "current_task": current_task,        "tasks": task_history    }        return jsonify(response)@app.route('/task/<task_id>')def get_task_details(task_id):    """Get details for a specific task"""    # Find task in history    task = None    for t in task_history:        if t["id"] == task_id:            task = t            break        if not task:        return jsonify({"error": "Task not found"}), 404        # Create result with full task details    result = task.copy()        # Add additional information based on task status    if task.get("status") == "completed":        # Add links to results        if task["type"] == "ingest":            result["links"] = {                "specs": f"/download/{task_id}/specs",                "reconstructed": f"/download/{task_id}/reconstructed"            }        elif task["type"] == "mimic":            result["links"] = {                "mimicked": f"/download/{task_id}/mimicked"            }        result["target_language"] = task.get("target_language")    result["source_task_id"] = task.get("source_task_id")        if task.get("status") == "error" and "error" in task:        result["error_details"] = task["error"]        return jsonify(result)@app.route('/download/<task_id>/<path:file_type>')def download_results(task_id, file_type):    """Download results as a ZIP file"""    # Find task in history    task = None    for t in task_history:        if t["id"] == task_id:            task = t            break        if not task or task["status"] != "completed":        return jsonify({"error": "Task not found or not completed"}), 404        import zipfile    import tempfile        # Create a temporary file for the ZIP    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:        temp_path = temp_file.name        try:        # Create ZIP file        with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zipf:            # Add files based on file type and task type            if task["type"] == "ingest" and file_type == "specs":                # Add spec files                if "result" in task and "spec_files" in task["result"]:                    for spec_file in task["result"]["spec_files"]:                        zipf.write(spec_file, os.path.basename(spec_file))                        elif task["type"] == "ingest" and file_type == "reconstructed":                # Add reconstructed files                if "result" in task and "reconstructed_files" in task["result"]:                    base_dir = os.path.dirname(task["result"]["reconstructed_files"][0])                    for reconstructed_file in task["result"]["reconstructed_files"]:                        # Strip the base directory path                        arcname = os.path.relpath(reconstructed_file, os.path.dirname(base_dir))                        zipf.write(reconstructed_file, arcname)                        elif task["type"] == "mimic" and file_type == "mimicked":                # Add mimicked files                if "result" in task and "mimicked_files" in task["result"]:                    base_dir = os.path.dirname(task["result"]["mimicked_files"][0])                    for mimicked_file in task["result"]["mimicked_files"]:                        # Strip the base directory path                        arcname = os.path.relpath(mimicked_file, os.path.dirname(base_dir))                        zipf.write(mimicked_file, arcname)                        else:                return jsonify({"error": "Invalid file type for this task"}), 400                # Send the file        return send_file(            temp_path,            as_attachment=True,            download_name=f"{file_type}_{task_id}.zip",            mimetype='application/zip'        )        except Exception as e:        logger.error(f"Error creating ZIP file: {str(e)}", exc_info=True)        return jsonify({"error": "Error creating download file"}), 500@app.route('/settings', methods=['GET', 'POST'])def settings():    """Settings page for configuring Ollama models and parameters"""    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")        if request.method == 'POST':        try:            # Load current config            with open(config_path, 'r') as f:                config = json.load(f)                        # Update with form values            config["ollama_settings"]["default_model"] = request.form.get("default_model")            config["ollama_settings"]["temperature"] = float(request.form.get("temperature", 0.2))            config["ollama_settings"]["max_tokens"] = int(request.form.get("max_tokens", 4096))                        # Save updated config            with open(config_path, 'w') as f:                json.dump(config, f, indent=2)                        return redirect(url_for('settings', message="Settings updated successfully"))                    except Exception as e:            logger.error(f"Error updating settings: {str(e)}", exc_info=True)            return render_template('settings.html', error=str(e))        # GET request - load and display settings    try:        # Load config        with open(config_path, 'r') as f:            config = json.load(f)                # Get available models from Ollama        available_models = []        if kaleidoscope and kaleidoscope.ollama:            try:                models_response = kaleidoscope.ollama.list_models()                if models_response:                    available_models = [model["name"] for model in models_response]            except Exception as e:                logger.error(f"Error fetching models: {str(e)}")                # Add current configured models if not in list        current_model = config["ollama_settings"]["default_model"]        if current_model not in available_models:            available_models.append(current_model)                return render_template('settings.html',                                config=config,                                available_models=available_models,                               message=request.args.get('message'))                                   except Exception as e:        logger.error(f"Error loading settings: {str(e)}", exc_info=True)        return render_template('settings.html', error=str(e))def start_server(work_dir=None, host="127.0.0.1", port=5000):    """    Start the web server        Args:        work_dir: Working directory        host: Host address to bind        port: Port to listen on    """    global kaleidoscope, worker_thread, running        # Initialize Kaleidoscope    work_dir = work_dir or os.path.join(os.getcwd(), "kaleidoscope_workdir")    kaleidoscope = KaleidoscopeCore(work_dir=work_dir)        # Start worker thread    running = True    worker_thread = threading.Thread(target=worker_loop)    worker_thread.daemon = True    worker_thread.start()        # Create HTML templates directory if it doesn't exist    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")    os.makedirs(templates_dir, exist_ok=True)        # Create static files directory if it doesn't exist    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")    os.makedirs(static_dir, exist_ok=True)    os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)    os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)        # Create index.html template if it doesn't exist    index_path = os.path.join(templates_dir, "index.html")    if not os.path.exists(index_path):        with open(index_path, 'w') as f:            f.write("""<!DOCTYPE html><html lang="en"><head>    <meta charset="UTF-8">    <meta name="viewport" content="width=device-width, initial-scale=1.0">    <title>Kaleidoscope AI</title>    <link rel="stylesheet" href="/static/css/styles.css">    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">        <div class="container-fluid">            <a class="navbar-brand" href="/">Kaleidoscope AI</a>            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">                <span class="navbar-toggler-icon"></span>            </button>            <div class="collapse navbar-collapse" id="navbarNav">                <ul class="navbar-nav">                    <li class="nav-item">                        <a class="nav-link active" href="/">Home</a>                    </li>                    <li class="nav-item">                        <a class="nav-link" href="/settings">Settings</a>                    </li>                </ul>            </div>        </div>    </nav>    <div class="container mt-4">        <div class="row">            <div class="col-lg-12">                <div class="card mb-4">                    <div class="card-header bg-primary text-white">                        <h4>Software Ingestion</h4>                    </div>                    <div class="card-body">                        <form id="upload-form" enctype="multipart/form-data">                            <div class="mb-3">                                <label for="file" class="form-label">Select software file to ingest</label>                                <input class="form-control" type="file" id="file" name="file">                                <div class="form-text">Supported file types: binaries (exe, dll, so), source code (py, js, c, cpp, java)</div>                            </div>                            <button type="submit" class="btn btn-primary">Upload & Analyze</button>                        </form>                        <div id="upload-progress" class="mt-3 d-none">                            <div class="alert alert-processing">                                <div class="d-flex align-items-center">                                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>                                    <span>Processing... This may take some time.</span>                                </div>                            </div>                        </div>                    </div>                </div>                <div id="task-section" class="d-none">                    <div class="card mb-4">                        <div class="card-header bg-info text-white">                            <h4>Current Task</h4>                        </div>                        <div class="card-body">                            <div id="current-task-info"></div>                        </div>                    </div>                </div>                <div id="mimic-section" class="d-none">                    <div class="card mb-4">                        <div class="card-header bg-success text-white">                            <h4>Generate Mimicked Software</h4>                        </div>                        <div class="card-body">                            <form id="mimic-form">                                <input type="hidden" id="source-task-id" name="source-task-id">                                <div class="mb-3">                                    <label for="target-language" class="form-label">Target Language</label>                                    <select class="form-select" id="target-language" name="target-language">                                        <option value="python">Python</option>                                        <option value="javascript">JavaScript</option>                                        <option value="cpp">C++</option>                                    </select>                                </div>                                <button type="submit" class="btn btn-success">Generate Mimicked Software</button>                            </form>                        </div>                    </div>                </div>                <div id="result-section" class="d-none">                    <div class="card mb-4">                        <div class="card-header bg-success text-white">                            <h4>Results</h4>                        </div>                        <div class="card-body">                            <div id="result-content"></div>                        </div>                    </div>                </div>                <div class="card">                    <div class="card-header bg-secondary text-white">                        <h4>Task History</h4>                    </div>                    <div class="card-body">                        <div id="task-history" class="list-group"></div>                    </div>                </div>            </div>        </div>    </div>    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>    <script src="/static/js/main.js"></script></body></html>""")        # Create settings.html template    settings_path = os.path.join(templates_dir, "settings.html")    if not os.path.exists(settings_path):        with open(settings_path, 'w') as f:            f.write("""<!DOCTYPE html><html lang="en"><head>    <meta charset="UTF-8">    <meta name="viewport" content="width=device-width, initial-scale=1.0">    <title>Settings - Kaleidoscope AI</title>    <link rel="stylesheet" href="/static/css/styles.css">    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">        <div class="container-fluid">            <a class="navbar-brand" href="/">Kaleidoscope AI</a>            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">                <span class="navbar-toggler-icon"></span>            </button>            <div class="collapse navbar-collapse" id="navbarNav">                <ul class="navbar-nav">                    <li class="nav-item">                        <a class="nav-link" href="/">Home</a>                    </li>                    <li class="nav-item">                        <a class="nav-link active" href="/settings">Settings</a>                    </li>                </ul>            </div>        </div>    </nav>    <div class="container mt-4">        <h1>Kaleidoscope AI Settings</h1>                {% if message %}        <div class="alert alert-success">            {{ message }}        </div>        {% endif %}                {% if error %}        <div class="alert alert-danger">            Error: {{ error }}        </div>        {% endif %}                <div class="card mt-4">            <div class="card-header bg-primary text-white">                <h4>Ollama Model Settings</h4>            </div>            <div class="card-body">                <form method="post">                    <div class="mb-3">                        <label for="default_model" class="form-label">Default Model</label>                        <select class="form-select" id="default_model" name="default_model">                            {% for model in available_models %}                            <option value="{{ model }}" {% if config.ollama_settings.default_model == model %}selected{% endif %}>{{ model }}</option>                            {% endfor %}                        </select>                        <div class="form-text">The model used for generating specifications and code.</div>                    </div>                    <div class="mb-3">                        <label for="temperature" class="form-label">Temperature</label>                        <input type="range" class="form-range" min="0" max="1" step="0.1" id="temperature" name="temperature" value="{{ config.ollama_settings.temperature }}">                        <div class="form-text">Current value: <span id="temperature-value">{{ config.ollama_settings.temperature }}</span></div>                        <div class="form-text">Lower values (0.0-0.3) for more deterministic outputs, higher values for more creative outputs.</div>                    </div>                    <div class="mb-3">                        <label for="max_tokens" class="form-label">Max Tokens</label>                        <input type="number" class="form-control" id="max_tokens" name="max_tokens" value="{{ config.ollama_settings.max_tokens }}">                        <div class="form-text">Maximum number of tokens to generate for each response.</div>                    </div>                    <button type="submit" class="btn btn-primary">Save Settings</button>                </form>            </div>        </div>                <div class="card mt-4">            <div class="card-header bg-info text-white">                <h4>Manage Ollama Models</h4>            </div>            <div class="card-body">                <p>You can manage your Ollama models outside of Kaleidoscope AI using the Ollama CLI:</p>                <pre class="bg-light p-3 rounded"># List available modelsollama list# Pull a new modelollama pull codellamaollama pull llama2ollama pull mistral# Get model infoollama show codellama                </pre>                <p>Learn more at <a href="https://ollama.ai" target="_blank">ollama.ai</a></p>            </div>        </div>    </div>    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>    <script>        // Update temperature value display        const temperatureSlider = document.getElementById('temperature');        const temperatureValue = document.getElementById('temperature-value');                temperatureSlider.addEventListener('input', function() {            temperatureValue.textContent = this.value;        });    </script></body></html>""")        # Create CSS file if it doesn't exist    css_path = os.path.join(static_dir, "css", "styles.css")    if not os.path.exists(css_path):        with open(css_path, 'w') as f:            f.write("""body {    background-color: #f8f9fa;    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;}.navbar-brand {    font-weight: bold;    letter-spacing: 1px;}.card {    border-radius: 10px;    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);    margin-bottom: 20px;}.card-header {    background-color: #f1f8ff;    border-bottom: 1px solid rgba(0, 0, 0, 0.125);}.task-item {    transition: all 0.3s ease;}.task-item:hover {    background-color: #f1f8ff;}.task-item.active {    background-color: #e2f0fd;    border-color: #90c8f8;}.alert-processing {    background-color: #fff8e1;    border-color: #ffe082;    color: #ff8f00;}.alert-completed {    background-color: #e8f5e9;    border-color: #a5d6a7;    color: #2e7d32;}.alert-error {    background-color: #ffebee;    border-color: #ef9a9a;    color: #c62828;}""")        # Create JavaScript file if it doesn't exist    js_path = os.path.join(static_dir, "js", "main.js")    if not os.path.exists(js_path):        with open(js_path, 'w') as f:            f.write("""document.addEventListener('DOMContentLoaded', function() {    // Elements    const uploadForm = document.getElementById('upload-form');    const uploadProgress = document.getElementById('upload-progress');    const taskSection = document.getElementById('task-section');    const currentTaskInfo = document.getElementById('current-task-info');    const mimicSection = document.getElementById('mimic-section');    const mimicForm = document.getElementById('mimic-form');    const sourceTaskId = document.getElementById('source-task-id');    const resultSection = document.getElementById('result-section');    const resultContent = document.getElementById('result-content');    const taskHistory = document.getElementById('task-history');        // State    let statusPollInterval;    let latestIngestTaskId = null;        // Start polling for status    startStatusPolling();        // Event listeners    uploadForm.addEventListener('submit', handleUpload);    mimicForm.addEventListener('submit', handleMimic);        // Functions    function handleUpload(event) {        event.preventDefault();                const fileInput = document.getElementById('file');        if (!fileInput.files.length) {            alert('Please select a file to upload');            return;        }                const formData = new FormData();        formData.append('file', fileInput.files[0]);                uploadProgress.classList.remove('d-none');                fetch('/upload', {            method: 'POST',            body: formData        })        .then(response => response.json())        .then(data => {            // Set the latest ingest task ID            latestIngestTaskId = data.task_id;            // Clear the file input            fileInput.value = '';        })        .catch(error => {            console.error('Error uploading file:', error);            alert('Error uploading file');            uploadProgress.classList.add('d-none');        });    }        function handleMimic(event) {        event.preventDefault();                const targetLanguage = document.getElementById('target-language').value;                const formData = new FormData();        formData.append('source_task_id', sourceTaskId.value);        formData.append('target_language', targetLanguage);                mimicSection.classList.add('d-none');        uploadProgress.classList.remove('d-none');                fetch('/mimic', {            method: 'POST',            body: formData        })        .then(response => response.json())        .then(data => {            // Tasks are being monitored by the status poll            console.log('Mimic task initiated:', data.task_id);        })        .catch(error => {            console.error('Error initiating mimic task:', error);            alert('Error initiating mimic task');            uploadProgress.classList.add('d-none');        });    }        function startStatusPolling() {        // Poll for task status every 2 seconds        statusPollInterval = setInterval(fetchStatus, 2000);    }        function fetchStatus() {        fetch('/status')            .then(response => response.json())            .then(data => {                updateTaskStatus(data);                updateTaskHistory(data.tasks);            })            .catch(error => {                console.error('Error fetching status:', error);            });    }        function updateTaskStatus(data) {        if (data.current_task) {            // Show task section and update with current task info            taskSection.classList.remove('d-none');            uploadProgress.classList.remove('d-none');                        const task = data.current_task;            let statusHtml = `                <div class="alert alert-processing">                    <h5>Processing ${task.type === 'ingest' ? 'Ingestion' : 'Mimicry'} Task</h5>                    <p>Task ID: ${task.id}</p>                    <p>Status: ${task.status}</p>                    <div class="progress">                        <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>                    </div>                </div>            `;                        currentTaskInfo.innerHTML = statusHtml;        } else {            // Hide progress indicators if no active task            uploadProgress.classList.add('d-none');                        // Check if we have a completed task and show results            const completedTasks = data.tasks.filter(task => task.status === 'completed');            if (completedTasks.length > 0) {                // Show the most recent completed task if it matches our latest initiated task                const latestCompletedTask = completedTasks[completedTasks.length - 1];                                if (latestCompletedTask.id === latestIngestTaskId) {                    // Show mimic section with this task as source                    mimicSection.classList.remove('d-none');                    sourceTaskId.value = latestIngestTaskId;                                        // Reset latest ingest task ID to avoid showing mimic section multiple times                    latestIngestTaskId = null;                }            }        }    }        function updateTaskHistory(tasks) {        if (!tasks || tasks.length === 0) {            taskHistory.innerHTML = '<p>No tasks yet</p>';            return;        }                // Clear existing content        taskHistory.innerHTML = '';                // Sort tasks by timestamp (newest first)        const sortedTasks = [...tasks].sort((a, b) => b.timestamp - a.timestamp);                // Add each task to the history        sortedTasks.forEach(task => {            let statusClass = '';            let statusText = task.status;                        if (task.status === 'completed') {                statusClass = 'text-success';                statusText = 'Completed';            } else if (task.status === 'processing') {                statusClass = 'text-warning';                statusText = 'Processing...';            } else if (task.status === 'error') {                statusClass = 'text-danger';                statusText = 'Error';            }                        const taskTime = new Date(task.timestamp * 1000).toLocaleString();            const taskTypeName = task.type === 'ingest' ? 'Ingestion' : 'Mimicry';                        let taskItemHtml = `                <div class="list-group-item task-item">                    <div class="d-flex w-100 justify-content-between">                        <h5 class="mb-1">${taskTypeName} Task</h5>                        <small>${taskTime}</small>                    </div>                    <p class="mb-1">ID: ${task.id}</p>                    <p class="mb-1 ${statusClass}">Status: ${statusText}</p>            `;                        // Add links for completed tasks            if (task.status === 'completed') {                taskItemHtml += '<div class="mt-2">';                                if (task.type === 'ingest') {                    taskItemHtml += `                        <a href="/download/${task.id}/specs" class="btn btn-sm btn-outline-primary me-2">Download Specs</a>                        <a href="/download/${task.id}/reconstructed" class="btn btn-sm btn-outline-success">Download Reconstructed</a>                    `;                } else if (task.type === 'mimic') {                    taskItemHtml += `                        <a href="/download/${task.id}/mimicked" class="btn btn-sm btn-outline-primary">Download Mimicked (${task.target_language})</a>                    `;                }                                taskItemHtml += '</div>';            }                        // Show error details if there was an error            if (task.status === 'error' && task.error) {                taskItemHtml += `<p class="text-danger mt-2">Error: ${task.error}</p>`;            }                        taskItemHtml += '</div>';                        taskHistory.innerHTML += taskItemHtml;        });    }});""")        # Run the Flask app    logger.info(f"Starting web server on {host}:{port}")    app.run(host=host, port=port, debug=False)def main():    """Main entry point for the web interface"""    parser = argparse.ArgumentParser(description="Kaleidoscope AI Web Interface")    parser.add_argument("--work-dir", "-w", help="Working directory", default=None)    parser.add_argument("--host", help="Host address to bind", default="127.0.0.1")    parser.add_argument("--port", "-p", help="Port to listen on", type=int, default=5000)        args = parser.parse_args()        try:        start_server(work_dir=args.work_dir, host=args.host, port=args.port)    except Exception as e:        logger.error(f"Error starting server: {str(e)}", exc_info=True)        return 1        return 0if __name__ == "__main__":    sys.exit(main())
