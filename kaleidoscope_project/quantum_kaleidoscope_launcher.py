#!/usr/bin/env python3
"""
Quantum Kaleidoscope Launcher
=============================

A launcher script for the Enhanced Quantum Kaleidoscope System.
This launches both the main system and the advanced visualizer.
"""

import os
import sys
import time
import subprocess
import threading
import argparse
import signal
import logging
# Ensure this import works after patching
from visualization_integration import patch_system

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("KaleidoscopeLauncher")

class ProcessManager:
    def __init__(self):
        self.processes = {}
        self.stop_event = threading.Event()

    def start_process(self, name, cmd, cwd=None):
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd
            )
            self.processes[name] = process
            threading.Thread(
                target=self._monitor_process_output,
                args=(name, process),
                daemon=True
            ).start()
            logger.info(f"Started process {name} (PID: {process.pid})")
            return True
        except Exception as e:
            logger.error(f"Error starting process {name}: {e}")
            return False

    def _monitor_process_output(self, name, process):
        while not self.stop_event.is_set():
            if process.poll() is not None:
                if process.returncode != 0:
                    logger.error(f"Process {name} terminated with code {process.returncode}")
                else:
                    logger.info(f"Process {name} terminated normally")
                # Attempt to remove from processes dict if terminated
                if name in self.processes:
                    try:
                        del self.processes[name]
                    except KeyError:
                        pass # Might have been removed by stop_all already
                break # Exit monitoring thread

            # Read stdout non-blockingly (less reliable across platforms)
            # A more robust solution might use select or dedicated threads per stream
            try:
                line = process.stdout.readline()
                if line:
                    logger.info(f"[{name}] {line.strip()}")
            except Exception: # Handle potential IO errors
                 pass

            try:
                line = process.stderr.readline()
                if line:
                    logger.error(f"[{name}] {line.strip()}")
            except Exception:
                 pass

            time.sleep(0.1) # Prevent busy-waiting

    def stop_all(self):
        self.stop_event.set()
        # Iterate over a copy of the keys, as _monitor_process_output might modify the dict
        for name in list(self.processes.keys()):
             if name in self.processes:
                 process = self.processes[name]
                 logger.info(f"Stopping process {name} (PID: {process.pid})")
                 try:
                     # Try terminating gracefully first
                     process.terminate()
                     try:
                         process.wait(timeout=5) # Wait up to 5 seconds
                     except subprocess.TimeoutExpired:
                         logger.warning(f"Process {name} did not terminate gracefully, forcing kill...")
                         process.kill()
                 except Exception as e:
                     logger.error(f"Error stopping process {name}: {e}")
                     try:
                          process.kill() # Ensure it's killed on error
                     except:
                          pass # Ignore errors during forced kill
                 # Remove after attempting to stop
                 if name in self.processes:
                      del self.processes[name]
        logger.info("All managed processes stopped.")


def get_script_path(script_name):
    # Assumes this launcher is run from the integrated_system directory
    launcher_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(launcher_dir, script_name)

def launch_system(data_dir, main_port, visualizer_port, auto_gen):
    logger.info("Starting Quantum Kaleidoscope System...")
    process_mgr = ProcessManager()
    os.makedirs(data_dir, exist_ok=True)

    # Determine the main system script (likely the unified one after integration)
    main_script = get_script_path("unified_quantum_kaleidoscope.py")
    visualizer_script = get_script_path("quantum_visualizer_new.py")

    if not os.path.exists(main_script):
        logger.error(f"Main system script not found: {main_script}")
        # Fallback check (might be useful if integration renamed differently)
        alt_main_script = get_script_path("enhanced_quantum_kaleidoscope.py")
        if os.path.exists(alt_main_script):
             logger.warning(f"Using fallback main script: {alt_main_script}")
             main_script = alt_main_script
        else:
             return None # Cannot proceed

    if not os.path.exists(visualizer_script):
         logger.error(f"Visualizer script not found: {visualizer_script}")
         # Allow system to start without visualizer? Or return None?
         # return None # For now, fail if visualizer missing

    # --- Launch main system ---
    main_cmd = [
        sys.executable, # Use the same python that's running the launcher
        main_script,
        "--data-dir", data_dir,
        "--port", str(main_port)
        # Add other necessary args for the main script based on its argparse setup
    ]
    if auto_gen:
        main_cmd.append("--auto-gen") # Assuming the main script supports this flag

    logger.info(f"Launching main system: {' '.join(main_cmd)}")
    if not process_mgr.start_process("main", main_cmd):
        logger.error("Failed to start main system")
        return None # Stop if main system fails

    logger.info("Waiting for main system to initialize...")
    time.sleep(5) # Increased wait time

    # --- Launch visualizer ---
    visualizer_cmd = [
        sys.executable,
        visualizer_script,
        "--api-port", str(main_port),
        "--port", str(visualizer_port)
    ]

    logger.info(f"Launching visualizer: {' '.join(visualizer_cmd)}")
    if not process_mgr.start_process("visualizer", visualizer_cmd):
        # Don't necessarily fail if only the visualizer fails
        logger.error("Failed to start visualizer, main system might still be running.")

    logger.info(f"""
===========================================================
Quantum Kaleidoscope System Attempting Start...
===========================================================
Main System API should be at: http://localhost:{main_port}
Visualizer should be at: http://localhost:{visualizer_port}
===========================================================
Check logs for confirmation. Press Ctrl+C to stop the launcher and processes.
===========================================================
""")
    # Apply visualization patch (added during integration script execution previously)
    # Assuming 'system' is accessible via some mechanism after launch_system runs
    # This patching logic might need adjustment based on how the main system is structured
    # It's safer if the main system *imports* and calls patch_system itself.
    # patch_system(process_mgr) # This line was likely incorrect placement, patching needs the system *instance*

    return process_mgr

def main():
    parser = argparse.ArgumentParser(description="Quantum Kaleidoscope Launcher")
    # Use relative paths default assuming ran from integrated_system dir
    parser.add_argument("--data-dir", type=str, default="./data",
                        help="Data directory (relative to integrated system dir)")
    parser.add_argument("--main-port", type=int, default=8000,
                        help="Port for main system API")
    parser.add_argument("--visualizer-port", type=int, default=8081,
                        help="Port for visualizer")
    parser.add_argument("--auto-gen", action="store_true",
                        help="Enable auto-generation in the main system (if supported)")

    args = parser.parse_args()

    # Ensure data dir exists relative to script execution
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir_abs = os.path.abspath(os.path.join(script_dir, args.data_dir))

    process_mgr = launch_system(
        data_dir=data_dir_abs, # Pass absolute path to subprocess
        main_port=args.main_port,
        visualizer_port=args.visualizer_port,
        auto_gen=args.auto_gen
    )

    if not process_mgr:
        logger.critical("Failed to launch system.")
        sys.exit(1)

    # Keep launcher running, wait for interrupt
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received. Stopping processes...")
        process_mgr.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Keep the main thread alive while monitoring threads run
    try:
        while True:
             # Check if any process is still running
             if not process_mgr.processes:
                  logger.info("All managed processes have terminated.")
                  break
             time.sleep(1)
    except Exception as e:
         logger.error(f"Launcher error: {e}")
    finally:
         logger.info("Launcher exiting.")
         process_mgr.stop_all() # Ensure cleanup on exit


if __name__ == "__main__":
    main()
