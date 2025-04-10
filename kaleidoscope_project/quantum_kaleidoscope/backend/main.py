import os
import sys
import argparse
import logging
import json
from typing import Dict, Any, Optional

# --- Configuration ---
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_WORK_DIR = "kaleidoscope_workdir"
DEFAULT_LOG_LEVEL = "INFO"

# Set up initial basic logging config in case config file fails
logging.basicConfig(
    level=DEFAULT_LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("KaleidoscopeCLI")

# --- Import Core Modules ---
try:
    from core.kaleidoscope_core import KaleidoscopeCore
    from web.kaleidoscope_web import start_server
except ImportError as e:
    logger.error(f"Error importing core modules: {e}", exc_info=True)
    logger.error("Please ensure:")
    logger.error("  1. You are in the 'kaleidoscope_project_organized' directory.")
    logger.error("  2. Your virtual environment is activated.")
    logger.error("  3. You have run 'pip install -e .' successfully.")
    sys.exit(1)

# --- Helper Functions ---
def load_config(config_path: str) -> Dict[str, Any]:
    """Loads configuration from a JSON file."""
    logger.info(f"Loading configuration from: {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info("Configuration loaded successfully.")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON configuration file: {config_path} - {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}", exc_info=True)
        raise

def setup_logging(config: Dict[str, Any], log_level_arg: Optional[str]):
    """Configures logging based on config file and command-line args."""
    log_config = config.get("logging", {})
    level_name = log_level_arg or log_config.get("level", DEFAULT_LOG_LEVEL).upper()
    log_level = getattr(logging, level_name, logging.INFO)

    handlers = []
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-8s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    handlers.append(console_handler)

    log_file = log_config.get("file")
    if log_file:
        try:
            log_dir = config.get("paths", {}).get("log_dir")
            if log_dir:
                log_path = os.path.join(log_dir, log_file)
                os.makedirs(log_dir, exist_ok=True)
            else:
                log_path = os.path.join(os.path.dirname(DEFAULT_CONFIG_FILE), log_file)
                os.makedirs(os.path.dirname(log_path), exist_ok=True)

            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-8s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
            handlers.append(file_handler)
            logger.info(f"Logging to file: {log_path}")
        except Exception as e:
            logger.error(f"Failed to configure file logging to {log_file}: {e}")

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for handler in handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
    logging.getLogger("KaleidoscopeCLI").setLevel(log_level)
    logging.getLogger("KaleidoscopeCore").setLevel(log_level)
    logging.getLogger("KaleidoscopeWeb").setLevel(log_level)
    logger.info(f"Logging level set to: {level_name}")

# --- Main Execution ---
def main():
    """Main entry point for Kaleidoscope AI CLI"""
    parser = argparse.ArgumentParser(
        description="Kaleidoscope AI - Software Ingestion & Mimicry System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--config", "-c", default=DEFAULT_CONFIG_FILE, help="Path to configuration JSON file.")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help="Set the logging level (overrides config file).")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest and analyze software", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ingest_parser.add_argument("--file", "-f", required=True, help="Path to software file to ingest")
    ingest_parser.add_argument("--work-dir", "-w", help="Working directory for output files.", default=None)

    mimic_parser = subparsers.add_parser("mimic", help="Generate mimicked software from specification", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    mimic_parser.add_argument("--spec", "-s", required=True, help="Path to specification file (.md assumed)")
    mimic_parser.add_argument("--language", "-l", required=True,
                              choices=["python", "javascript", "cpp"],
                              help="Target language for mimicked software")
    mimic_parser.add_argument("--work-dir", "-w", help="Working directory for output files.", default=None)

    web_parser = subparsers.add_parser("web", help="Start the web interface", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    web_parser.add_argument("--host", help="Host address to bind (overrides config).", default=None)
    web_parser.add_argument("--port", "-p", type=int, help="Port to listen on (overrides config).", default=None)
    web_parser.add_argument("--work-dir", "-w", help="Working directory for output files.", default=None)

    args = parser.parse_args()

    try:
        config = load_config(args.config)
        setup_logging(config, args.log_level)
    except Exception:
        logger.critical("Failed to load configuration or setup logging. Exiting.")
        return 1

    work_dir_cli = getattr(args, 'work_dir', None)
    work_dir = work_dir_cli or config.get("paths", {}).get("data_dir", DEFAULT_WORK_DIR)
    logger.debug(f"Using working directory: {work_dir}")
    abs_work_dir = os.path.abspath(work_dir)
    try:
        os.makedirs(abs_work_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create working directory '{abs_work_dir}': {e}")
        return 1

    try:
        kaleidoscope = None
        if args.command in ["ingest", "mimic"]:
            llm_config = config.get("llm", {})
            llm_endpoint = llm_config.get("api_base")
            max_workers = config.get("max_workers", 4)
            logger.debug(f"Initializing KaleidoscopeCore with work_dir='{abs_work_dir}', llm_endpoint='{llm_endpoint}'")
            kaleidoscope = KaleidoscopeCore(work_dir=abs_work_dir, llm_endpoint=llm_endpoint, max_workers=max_workers)

        if args.command == "ingest":
            if not kaleidoscope:
                logger.critical("KaleidoscopeCore failed to initialize.")
                return 1
            input_file = args.file
            if not os.path.isfile(input_file):
                logger.error(f"Input path is not a file or does not exist: {input_file}")
                return 1
            max_file_size = config.get("processing", {}).get("max_file_size", 100000000)  # Default 100MB
            if os.path.getsize(input_file) > max_file_size:
                logger.error(f"File too large: {input_file} (size: {os.path.getsize(input_file)} bytes, max: {max_file_size} bytes)")
                return 1

            logger.info(f"Starting ingestion for: {input_file}")
            result = kaleidoscope.ingest_software(input_file)
            status = result.get('status', 'unknown')
            logger.info(f"Ingestion completed with status: {status}")
            if status == "completed":
                spec_files = result.get('spec_files', [])
                reconstructed_files = result.get('reconstructed_files', [])
                logger.info(f"  Generated {len(spec_files)} specification files.")
                logger.info(f"  Generated {len(reconstructed_files)} reconstructed files.")
            elif status == "error":
                logger.error(f"  Ingestion Error: {result.get('error', 'Unknown error')}")
                return 1

        elif args.command == "mimic":
            if not kaleidoscope:
                logger.critical("KaleidoscopeCore failed to initialize.")
                return 1
            spec_file = args.spec
            if not os.path.isfile(spec_file):
                logger.error(f"Specification file not found or is not a file: {spec_file}")
                return 1
            if not spec_file.lower().endswith('.md'):
                logger.warning(f"Specification file {spec_file} does not have .md extension. Proceeding anyway.")

            spec_files = [spec_file]
            logger.info(f"Starting mimicry from {spec_file} into {args.language}")
            result = kaleidoscope.mimic_software(spec_files, args.language)
            status = result.get('status', 'unknown')
            logger.info(f"Mimicry completed with status: {status}")
            if status == "completed":
                mimicked_files = result.get('mimicked_files', [])
                mimicked_dir = result.get('mimicked_dir', 'N/A')
                logger.info(f"  Generated {len(mimicked_files)} mimicked files.")
                logger.info(f"  Output directory: {mimicked_dir}")
            elif status == "error":
                logger.error(f"  Mimicry Error: {result.get('error', 'Unknown error')}")
                return 1

        elif args.command == "web":
            web_config = config.get("web_interface", {})
            host = args.host or web_config.get("host", "127.0.0.1")
            port = args.port or web_config.get("port", 5000)
            logger.info(f"Starting web server on http://{host}:{port} with work_dir={abs_work_dir}")
            start_server(work_dir=abs_work_dir, host=host, port=port, config_path=os.path.abspath(args.config))

        return 0

    except FileNotFoundError as e:
        logger.error(f"A required file was not found: {e}", exc_info=True)
        return 1
    except KeyError as e:
        logger.error(f"Configuration key missing: {e}. Please check '{args.config}'.", exc_info=True)
        return 1
    except ImportError as e:
        logger.error(f"Import error: {e}. Ensure necessary dependencies are installed.", exc_info=True)
        return 1
    except Exception as e:
        logger.critical(f"An unexpected error occurred during command '{args.command}': {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    return_code = main()
    if return_code != 0:
        sys.exit(return_code)
