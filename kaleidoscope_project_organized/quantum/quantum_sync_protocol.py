#!/usr/bin/env python3
"""
Quantum Synchronization Protocol for Kaleidoscope AI ServerFleet

Handles synchronization between the Quantum Network Server and the main
Kaleidoscope AI orchestrator/fleet nodes. Manages state exchange, fault tolerance,
and performance optimization through SSH and WebSocket communication.
"""

import asyncio
import websockets
import json
import logging
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import paramiko # For SSH

# --- Configuration Loading ---
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json" # Assumes config.json is in project root

def load_configuration(config_path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Loads configuration from the main config.json file."""
    if not config_path.exists():
        logger.warning(f"Configuration file not found: {config_path}. Using defaults.")
        return {}
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading configuration from {config_path}: {e}", exc_info=True)
        return {}

# --- Logging Setup ---
# Assumes logging is configured by the main application entry point (e.g., main.py)
# If run standalone, basicConfig might be needed.
logger = logging.getLogger(__name__)

# --- Protocol Constants (Defaults, overridden by config) ---
MAX_RETRY_ATTEMPTS = 5
INITIAL_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 30.0
DEFAULT_SSH_TIMEOUT = 10
DEFAULT_WS_TIMEOUT = 10
DEFAULT_SYNC_INTERVAL = 5.0
DEFAULT_NODE_TIMEOUT = 60.0

class QuantumSynchronizationProtocol:
    """Manages synchronization between Quantum Server and Kaleidoscope nodes."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the synchronization protocol manager.

        Args:
            config (Dict[str, Any]): Loaded configuration dictionary.
        """
        self.config = config
        self.quantum_config = config.get("quantum_sync", {})
        self.server_url: str = self.quantum_config.get("server_url", "ws://localhost:8765")
        self.sync_interval: float = self.quantum_config.get("sync_interval", DEFAULT_SYNC_INTERVAL)
        self.node_timeout: float = self.quantum_config.get("node_timeout", DEFAULT_NODE_TIMEOUT)
        self.max_sync_attempts: int = self.quantum_config.get("max_sync_attempts", MAX_RETRY_ATTEMPTS)

        # SSH Configuration
        self.ssh_config = config.get("ssh_settings", {}) # Assuming ssh settings might be elsewhere
        self.ssh_username: str = self.ssh_config.get("username", "default_user") # Example key
        self.ssh_key_path: Optional[str] = self.ssh_config.get("key_path") # Example key
        self.ssh_timeout: int = self.ssh_config.get("timeout", DEFAULT_SSH_TIMEOUT)

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.fleet_nodes: Dict[str, Dict] = {} # node_id -> node_info (e.g., {'ip_address': ...})
        self.running: bool = False
        self.sync_task: Optional[asyncio.Task] = None

        logger.info(f"QuantumSyncProtocol initialized for server: {self.server_url}")

    async def connect_to_quantum_server(self) -> bool:
        """Establish WebSocket connection with exponential backoff."""
        current_delay = INITIAL_RETRY_DELAY
        for attempt in range(self.max_sync_attempts):
            try:
                logger.info(f"Attempting to connect to Quantum Server: {self.server_url} (Attempt {attempt + 1}/{self.max_sync_attempts})")
                # Add timeout to connection attempt
                self.websocket = await asyncio.wait_for(
                    websockets.connect(self.server_url, max_size=self.config.get('max_message_size', 10*1024*1024)),
                    timeout=DEFAULT_WS_TIMEOUT
                )
                await self.websocket.send(json.dumps({"type": "register", "node_id": "sync_protocol_manager", "name": "SyncManager"}))
                response = await asyncio.wait_for(self.websocket.recv(), timeout=DEFAULT_WS_TIMEOUT)
                logger.info(f"Received from server: {response}")
                if json.loads(response).get("type") == "welcome":
                     logger.info(f"Successfully connected to Quantum Server at {self.server_url}")
                     return True
                else:
                     logger.warning("Received unexpected welcome message.")
                     await self.websocket.close()
                     self.websocket = None

            except (websockets.exceptions.InvalidURI,
                    websockets.exceptions.InvalidHandshake,
                    websockets.exceptions.ConnectionClosedError,
                    ConnectionRefusedError,
                    asyncio.TimeoutError,
                    OSError) as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error during connection attempt {attempt + 1}: {e}", exc_info=True)

            if attempt < self.max_sync_attempts - 1:
                logger.info(f"Retrying connection in {current_delay:.1f} seconds...")
                await asyncio.sleep(current_delay)
                current_delay = min(current_delay * 2, MAX_RETRY_DELAY) # Exponential backoff
            else:
                 logger.error("Max connection attempts reached. Failed to connect.")

        return False

    async def close_connection(self) -> None:
        """Close the WebSocket connection."""
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.close()
                logger.info("WebSocket connection closed.")
            except Exception as e:
                logger.error(f"Error closing WebSocket connection: {e}", exc_info=True)
        self.websocket = None

    def update_fleet_nodes(self, nodes: List[Dict]) -> None:
        """Update the list of fleet nodes to synchronize with."""
        self.fleet_nodes = {node['id']: node for node in nodes if 'id' in node}
        logger.info(f"Updated fleet node list. Count: {len(self.fleet_nodes)}")

    async def execute_remote_command(self, node_info: Dict, command: str) -> Optional[str]:
        """
        Executes a command on a remote fleet node via SSH with enhanced security.

        Args:
            node_info (Dict): Dictionary containing node details (e.g., 'ip_address').
            command (str): The command to execute.

        Returns:
            Optional[str]: The command output (stdout) or None on failure.
        """
        if 'ip_address' not in node_info:
            logger.warning(f"Cannot execute command: Missing 'ip_address' for node {node_info.get('id')}")
            return None

        hostname = node_info['ip_address']
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.WarningPolicy()) # Or AutoAddPolicy, consider security implications

        try:
            logger.debug(f"Connecting SSH to {hostname} as {self.ssh_username}")
            connect_args = {
                "hostname": hostname,
                "username": self.ssh_username,
                "timeout": self.ssh_timeout,
                "allow_agent": False, # Generally safer unless agent forwarding is needed
                "look_for_keys": False # Explicitly provide key
            }
            if self.ssh_key_path and Path(self.ssh_key_path).exists():
                 connect_args["key_filename"] = self.ssh_key_path
            elif self.ssh_config.get("password"): # Fallback to password if key not found/specified
                 connect_args["password"] = self.ssh_config.get("password")
            else:
                 logger.error(f"SSH connection to {hostname} requires either a valid key_path or password in config.")
                 return None

            ssh.connect(**connect_args)

            logger.debug(f"Executing command on {hostname}: {command}")
            stdin, stdout, stderr = ssh.exec_command(command, timeout=self.ssh_timeout * 2) # Longer timeout for command itself
            exit_status = stdout.channel.recv_exit_status() # Wait for command completion

            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if exit_status == 0:
                logger.debug(f"Command successful on {hostname}. Output length: {len(output)}")
                return output
            else:
                logger.error(f"Command failed on {hostname} (Exit Status {exit_status}): {error}")
                return None

        except paramiko.AuthenticationException:
            logger.error(f"SSH Authentication failed for {self.ssh_username}@{hostname}. Check credentials/keys.")
            return None
        except paramiko.SSHException as ssh_ex:
            logger.error(f"SSH connection error to {hostname}: {ssh_ex}")
            return None
        except TimeoutError:
             logger.error(f"SSH connection or command timeout for {hostname}")
             return None
        except Exception as e:
            logger.error(f"Error executing remote command on {hostname}: {e}", exc_info=True)
            return None
        finally:
            ssh.close()
            logger.debug(f"SSH connection closed for {hostname}")


    async def synchronize_node_state(self, node_id: str, node_info: Dict) -> bool:
        """Synchronize state between quantum server and a fleet node."""
        if not self.websocket or self.websocket.closed:
            logger.warning("Cannot synchronize: WebSocket not connected.")
            if not await self.connect_to_quantum_server(): return False # Attempt reconnect

        logger.debug(f"Synchronizing state for node {node_id}...")
        try:
            # 1. Get current quantum state from server
            await self.websocket.send(json.dumps({"type": "get_node_state", "node_id": node_id}))
            response_str = await asyncio.wait_for(self.websocket.recv(), timeout=DEFAULT_WS_TIMEOUT)
            response_data = json.loads(response_str)

            if response_data.get("type") == "node_state" and "state" in response_data:
                quantum_state_data = response_data["state"]
                # 2. Send state to fleet node (e.g., via SSH command or another API)
                # Example: using SSH to update a config file or call an update script
                # Security Note: Sending raw state data might not be ideal. Consider sending derived metrics.
                state_json = json.dumps(quantum_state_data)
                # Escape quotes for shell command
                escaped_state = state_json.replace('"', '\\"')
                command = f"update-quantum-state --state \"{escaped_state}\"" # Example command on fleet node

                output = await self.execute_remote_command(node_info, command)
                if output is not None:
                    logger.debug(f"State synchronization command sent to {node_id}")
                    return True
                else:
                    logger.error(f"Failed to send state update command to {node_id}")
                    return False
            else:
                 logger.warning(f"Failed to get valid quantum state for node {node_id} from server: {response_data}")
                 return False

        except asyncio.TimeoutError:
             logger.error(f"Timeout during synchronization for node {node_id}")
             await self.close_connection() # Close potentially broken connection
             return False
        except websockets.exceptions.ConnectionClosed:
             logger.error(f"WebSocket closed during synchronization for node {node_id}")
             self.websocket = None # Mark as closed
             return False
        except Exception as e:
            logger.error(f"Error synchronizing node {node_id}: {e}", exc_info=True)
            return False


    async def _sync_loop(self) -> None:
        """Main background loop for periodic synchronization."""
        logger.info("Starting synchronization loop...")
        while self.running:
            start_time = time.time()
            logger.debug("Running sync cycle...")

            if not self.websocket or self.websocket.closed:
                if not await self.connect_to_quantum_server():
                    await asyncio.sleep(self.sync_interval) # Wait before retrying connect
                    continue # Skip sync cycle if connection failed

            sync_tasks = []
            # Create tasks for synchronizing each fleet node
            for node_id, node_info in self.fleet_nodes.items():
                 # Add check for node activity if available in node_info
                 if node_info.get("is_active", True):
                      sync_tasks.append(self.synchronize_node_state(node_id, node_info))

            if sync_tasks:
                 results = await asyncio.gather(*sync_tasks, return_exceptions=True)
                 success_count = sum(1 for r in results if r is True)
                 fail_count = len(results) - success_count
                 logger.debug(f"Sync cycle finished. Success: {success_count}, Failed: {fail_count}")
            else:
                 logger.debug("No active fleet nodes found to synchronize.")

            # Wait for the next interval
            elapsed = time.time() - start_time
            sleep_duration = max(0, self.sync_interval - elapsed)
            await asyncio.sleep(sleep_duration)

        logger.info("Synchronization loop stopped.")


    async def start(self) -> None:
        """Start the synchronization protocol."""
        if self.running:
            logger.warning("Sync protocol already running.")
            return
        self.running = True
        if not await self.connect_to_quantum_server():
             self.running = False # Failed to start if initial connection fails
             return

        # Start the background synchronization loop
        self.sync_task = asyncio.create_task(self._sync_loop())
        logger.info("Synchronization protocol started.")


    async def stop(self) -> None:
        """Stop the synchronization protocol."""
        if not self.running:
            return
        logger.info("Stopping synchronization protocol...")
        self.running = False
        # Cancel the background task
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                logger.info("Sync loop cancelled.")
        # Close WebSocket connection
        await self.close_connection()
        logger.info("Synchronization protocol stopped.")

# --- Main Execution (Example/Test) ---
async def run_sync_manager():
    """Example of running the sync manager."""
    config = load_configuration() # Load from default path
    sync_manager = QuantumSynchronizationProtocol(config)

    # Example fleet nodes (replace with actual fleet management)
    example_nodes = [
        {"id": "node-fleet-1", "ip_address": "192.168.1.101", "is_active": True},
        {"id": "node-fleet-2", "ip_address": "192.168.1.102", "is_active": True},
    ]
    sync_manager.update_fleet_nodes(example_nodes)

    await sync_manager.start()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(3600) # Sleep for an hour or until interrupted
    except asyncio.CancelledError:
        logger.info("Run task cancelled.")
    finally:
        await sync_manager.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kaleidoscope Quantum Sync Protocol Manager")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to the main config.json file")
    parser.add_argument("--log", default="INFO", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="Logging level")
    args = parser.parse_args()

    # Setup logging level
    log_level_to_set = getattr(logging, args.log.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level_to_set) # Root logger
    logger.setLevel(log_level_to_set) # This module's logger

    try:
        asyncio.run(run_sync_manager())
    except KeyboardInterrupt:
        logger.info("Sync manager stopped by user.")
