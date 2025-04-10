#!/usr/bin/env python3
"""
Kaleidoscope AI Web Interface
Provides Flask routes for interacting with KaleidoscopeCore with enhanced error handling and security.
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
import zipfile
from io import BytesIO
from typing import Optional, Dict, List, Any
from pathlib import Path
from flask import (
    Flask, render_template, request, jsonify, send_file, redirect, url_for, Response
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import jwt
from datetime import datetime, timedelta

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

# --- Logging Configuration ---
logger = logging.getLogger("KaleidoscopeWeb")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(PROJECT_ROOT / "kaleidoscope_web.log")
        ]
    )

# --- Flask App Setup ---
app = Flask(
    __name__,
    template_folder=SCRIPT_DIR / "templates",
    static_folder=SCRIPT_DIR / "static"
)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex()),
    MAX_CONTENT_LENGTH=100 * 1024 * 1024,  # 100MB upload limit
    UPLOAD_FOLDER=str(PROJECT_ROOT / "uploads")
)

# Security enhancements
Talisman(app, force_https=False)  # Enable HTTPS in production
limiter = Limiter(get_remote_address, app=app, default_limits=["100 per minute"])

# --- Global State ---
kaleidoscope: Optional[KaleidoscopeCore] = None
task_queue = queue.Queue()
current_task: Optional[Dict[str, Any]] = None
task_history: List[Dict[str, Any]] = []
worker_thread: Optional[threading.Thread] = None
running = threading.Event()
max_history_size = 20

ALLOWED_EXTENSIONS = {
    'exe', 'dll', 'so', 'dylib', 'bin',
    'js', 'mjs', 'py', 'c', 'cpp', 'h', 'hpp',
    'java', 'class', 'jar', 'go', 'rs',
    'php', 'rb', 'cs', 'asm', 's'
}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Worker Functions ---
def worker_loop() -> None:
    """Background worker to process queued tasks"""
    logger.info("Worker thread started")
    running.set()
    while running.is_set():
        try:
            task = task_queue.get(timeout=1.0)
            if task is None:
                continue

            with app.app_context():
                process_task(task)
            task_queue.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Worker loop error: {e}", exc_info=True)
            if current_task:
                current_task["status"] = "error"
                current_task["error"] = str(e)
                task_history.append(current_task.copy())
                trim_history()
    logger.info("Worker thread stopped")

def process_task(task: Dict[str, Any]) -> None:
    """Process a single task"""
    global current_task
    current_task = task
    task["status"] = "processing"
    logger.info(f"Processing task {task['id']} ({task['type']})")

    try:
        if task["type"] == "ingest":
            worker_ingest(task)
        elif task["type"] == "mimic":
            worker_mimic(task)
        else:
            task["status"] = "error"
            task["error"] = f"Unknown task type: {task['type']}"
    except Exception as e:
        logger.error(f"Task {task['id']} failed: {e}", exc_info=True)
        task["status"] = "error"
        task["error"] = str(e)
    finally:
        task_history.append(task.copy())
        trim_history()
        current_task = None

def worker_ingest(task: Dict[str, Any]) -> None:
    """Handle software ingestion"""
    if not kaleidoscope:
        raise RuntimeError("KaleidoscopeCore not initialized")
    file_path = task["file_path"]
    result = kaleidoscope.ingest_software(file_path)
    task.update(result)

def worker_mimic(task: Dict[str, Any]) -> None:
    """Handle software mimicry"""
    if not kaleidoscope:
        raise RuntimeError("KaleidoscopeCore not initialized")
    spec_path = task["spec_path"]
    target_language = task["target_language"]
    result = kaleidoscope.mimic_software([spec_path], target_language)
    task.update(result)

def trim_history() -> None:
    """Trim task history to max size"""
    global task_history
    with threading.Lock():
        while len(task_history) > max_history_size:
            task_history.pop(0)

# --- Flask Routes ---
@app.route('/')
def index() -> str:
    """Render main page"""
    template_path = app.template_folder / "index.html"
    if not template_path.exists():
        logger.warning("index.html not found")
        return "Kaleidoscope AI Web Interface - Template missing", 503
    return render_template("index.html")

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per minute")
def upload_file() -> Response:
    """Handle file upload for ingestion"""
    if not kaleidoscope:
        return jsonify({"error": "System not initialized"}), 503

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    try:
        filename = secure_filename(file.filename)
        upload_dir = Path(app.config['UPLOAD_FOLDER'])
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / filename
        file.save(file_path)
        logger.info(f"Uploaded file: {file_path}")

        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "type": "ingest",
            "file_path": str(file_path),
            "original_filename": filename,
            "timestamp": time.time(),
            "status": "pending"
        }
        task_queue.put(task)
        return jsonify({"task_id": task_id})
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({"error": "Upload failed"}), 500

@app.route('/mimic', methods=['POST'])
@limiter.limit("5 per minute")
def mimic_software() -> Response:
    """Handle software mimicry request"""
    if not kaleidoscope:
        return jsonify({"error": "System not initialized"}), 503

    data = request.form
    spec_path = data.get("spec_path")
    target_language = data.get("target_language")
    source_task_id = data.get("source_task_id")

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
        "status": "pending"
    }
    task_queue.put(task)
    return jsonify({"task_id": task_id})

@app.route('/status')
def get_status() -> Response:
    """Return task status"""
    with threading.Lock():
        return jsonify({
            "current_task": current_task.copy() if current_task else None,
            "tasks": task_history.copy()
        })

@app.route('/task/<task_id>')
def get_task_details(task_id: str) -> Response:
    """Get specific task details"""
    with threading.Lock():
        task = current_task if current_task and current_task["id"] == task_id else None
        if not task:
            task = next((t for t in task_history if t["id"] == task_id), None)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(task.copy())

@app.route('/download/<task_id>/<file_type>')
def download_results(task_id: str, file_type: str) -> Response:
    """Download task results as ZIP"""
    if not kaleidoscope:
        return jsonify({"error": "System not initialized"}), 503

    task = next((t for t in task_history if t["id"] == task_id and t["status"] == "completed"), None)
    if not task:
        return jsonify({"error": "Task not found or not completed"}), 404

    files_key = {
        "ingest": {"specs": "spec_files", "reconstructed": "reconstructed_files"},
        "mimic": {"mimicked": "mimicked_files"}
    }.get(task["type"], {}).get(file_type)
    if not files_key or files_key not in task:
        return jsonify({"error": "Invalid file type for task"}), 400

    files = task[files_key]
    if not files:
        return jsonify({"error": "No files available"}), 404

    zip_buffer = BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            base_dir = Path(kaleidoscope.work_dir)
            for file_path in files:
                if Path(file_path).exists():
                    arcname = Path(file_path).relative_to(base_dir)
                    zipf.write(file_path, arcname)
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=f"{file_type}_{task_id}.zip",
            mimetype="application/zip"
        )
    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        return jsonify({"error": "Failed to create ZIP"}), 500

@app.route('/settings', methods=['GET', 'POST'])
def settings() -> str:
    """Manage Ollama settings"""
    config_path = PROJECT_ROOT / "config.json"
    config = {}
    models = []
    error = None

    try:
        if config_path.exists():
            with config_path.open('r') as f:
                config = json.load(f)
        if kaleidoscope and config.get("llm", {}).get("provider") == "ollama":
            models = [m["name"] for m in kaleidoscope.ollama.list_models()]
    except Exception as e:
        error = f"Error loading settings: {e}"
        logger.error(error, exc_info=True)

    if request.method == "POST":
        try:
            with config_path.open('r') as f:
                config = json.load(f)
            llm = config.setdefault("llm", {})
            if llm.get("provider") == "ollama":
                llm["default_model"] = request.form.get("default_model", llm.get("default_model", "codellama"))
                llm["temperature"] = float(request.form.get("temperature", llm.get("temperature", 0.2)))
                llm["max_tokens"] = int(request.form.get("max_tokens", llm.get("max_tokens", 4096)))
            with config_path.open('w') as f:
                json.dump(config, f, indent=2)
            return redirect(url_for("settings", message="Settings updated"))
        except Exception as e:
            error = f"Error saving settings: {e}"
            logger.error(error, exc_info=True)

    return render_template("settings.html", config=config, models=models, error=error, message=request.args.get("message"))

# --- Error Handlers ---
@app.errorhandler(HTTPException)
def handle_http_exception(e: HTTPException) -> Response:
    """Handle HTTP errors"""
    return jsonify({"error": e.description}), e.code

@app.errorhandler(Exception)
def handle_uncaught_exception(e: Exception) -> Response:
    """Handle uncaught exceptions"""
    logger.error(f"Uncaught exception: {e}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500

# --- Server Startup ---
def start_server(
    work_dir: Optional[str] = None,
    host: str = "127.0.0.1",
    port: int = 5000,
    config_path: Optional[str] = None
) -> None:
    """Start the Flask server"""
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

    try:
        kaleidoscope = KaleidoscopeCore(
            work_dir=work_dir,
            llm_endpoint=config.get("llm", {}).get("api_base"),
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
    parser = argparse.ArgumentParser(description="Kaleidoscope AI Web Interface")
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
        sys.exit(1)
