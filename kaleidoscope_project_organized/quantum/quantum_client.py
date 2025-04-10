#!/usr/bin/env python3
"""
Quantum Network Client for Kaleidoscope AI

Connects to the Quantum Network Server, maintains a local quantum state,
and participates in distributed quantum computations and synchronization.
"""

import asyncio
import websockets
import json
import logging
import time
import uuid
import argparse
from pathlib import Path
import numpy as np
from typing import Dict, List, Any, Optional, Callable

# Use the QuantumState class potentially defined in quantum_server or a shared types module
# For standalone capability, redefining a compatible version here.
# If importing from quantum_server, ensure proper package structure.
try:
     # Assuming quantum_server is in the same package
     from .quantum_server import QuantumState
except ImportError:
     # Redefine if running standalone or import failed
     logging.warning("Could not import QuantumState from .quantum_server, using local definition.")
     # Simplified QuantumState for client (matching structure is important)
     class QuantumState:
          def __init__(self, dimension: int = 32):
               self.dimension = dimension
               self.state = np.zeros(dimension, dtype=complex)
               self.fidelity = 0.0
               self.creation_time = 0.0
               self.entangled_with = set()
          def serialize(self) -> Dict: return {} # Placeholder
          @classmethod
          def deserialize(cls, data: Dict) -> 'QuantumState': return cls() # Placeholder


# --- Configuration Loading ---
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

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
logger = logging.getLogger("QuantumClient")
# Assume root logger is configured by the application entry point

# --- Client Constants (Defaults, overridden by config) ---
DEFAULT_SERVER_URL = "ws://localhost:8765"
DEFAULT_HILBERT_DIM = 32
MAX_RECONNECT_ATTEMPTS = 5
INITIAL_RECONNECT_DELAY = 1.0
MAX_RECONNECT_DELAY = 30.0
WEBSOCKET_TIMEOUT = 10.0 # Timeout for send/recv

class QuantumNetworkClient:
    """Client node participating in the quantum network."""

    def __init__(self, config: Dict[str, Any], node_id: Optional[str] = None, name: Optional[str] = None):
        """
        Initialize the quantum client.

        Args:
            config (Dict[str, Any]): Loaded configuration dictionary.
            node_id (Optional[str]): Unique ID for this client node. Defaults to generated UUID.
            name (Optional[str]): Name for this client node. Defaults to Node-<id>.
        """
        self.config = config
        self.quantum_config = config.get("quantum_sync", {})
        self.system_config = config.get("system", {})

        self.server_url: str = self.quantum_config.get("server_url", DEFAULT_SERVER_URL)
        self.node_id: str = node_id or f"client_{uuid.uuid4().hex[:8]}"
        self.name: str = name or f"Node-{self.node_id}"
        self.dimension: int = self.system_config.get("dimension", DEFAULT_HILBERT_DIM)

        self.state: QuantumState = QuantumState(dimension=self.dimension)
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected: bool = False
        self.running: bool = False
        self.reconnect_attempts: int = 0
        self.message_handler: Optional[Callable[[Dict], None]] = None # Callback for received messages

        self.max_reconnect_attempts = self.quantum_config.get("max_reconnect_attempts", MAX_RECONNECT_ATTEMPTS)
        self.initial_reconnect_delay = self.quantum_config.get("initial_reconnect_delay", INITIAL_RECONNECT_DELAY)
        self.max_reconnect_delay = self.quantum_config.get("max_reconnect_delay", MAX_RECONNECT_DELAY)

        logger.info(f"QuantumClient initialized: ID={self.node_id}, Name={self.name}, Server={self.server_url}")

    def set_message_handler(self, handler: Callable[[Dict], None]):
        """Set a callback function to handle messages from the server."""
        self.message_handler = handler

    async def connect(self) -> bool:
        """Establish connection to the quantum server."""
        if self.is_connected:
            return True
        logger.info(f"Attempting connection to {self.server_url}...")
        try:
            # Connect with timeout and increased max_size
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                     self.server_url,
                     max_size=self.config.get('max_message_size', 10*1024*1024),
                     ping_interval=20, # Keep connection alive
                     ping_timeout=20
                ),
                timeout=WEBSOCKET_TIMEOUT
            )
            self.is_connected = True
            self.reconnect_attempts = 0 # Reset attempts on successful connect

            # Register with the server
            await self.send_message({
                "type": "register",
                "node_id": self.node_id,
                "name": self.name,
                "capabilities": ["compute", "storage"] # Example capabilities
            })
            logger.info(f"Connection established. Waiting for welcome message...")
            # Wait for welcome message implicitly handled by listen loop
            return True
        except (websockets.exceptions.InvalidURI,
                websockets.exceptions.InvalidHandshake,
                websockets.exceptions.ConnectionClosedError,
                ConnectionRefusedError,
                asyncio.TimeoutError,
                OSError) as e:
            logger.error(f"Connection failed: {e}")
            self.is_connected = False
            self.websocket = None
            return False
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}", exc_info=True)
            self.is_connected = False
            self.websocket = None
            return False

    async def close(self) -> None:
        """Gracefully close the connection."""
        self.running = False # Signal loops to stop
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.close(code=1000, reason="Client shutting down")
                logger.info("WebSocket connection closed.")
            except Exception as e:
                logger.error(f"Error during WebSocket close: {e}")
        self.is_connected = False
        self.websocket = None

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a JSON message to the server."""
        if not self.is_connected or not self.websocket:
            logger.warning("Cannot send message: Not connected.")
            return False
        try:
            message_json = json.dumps(message)
            await asyncio.wait_for(self.websocket.send(message_json), timeout=WEBSOCKET_TIMEOUT)
            logger.debug(f"Sent message type: {message.get('type')}")
            return True
        except asyncio.TimeoutError:
             logger.error("Timeout sending message.")
             await self.close() # Close potentially broken connection
             return False
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Cannot send message: Connection closed.")
            self.is_connected = False
            self.websocket = None
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            await self.close() # Assume connection is broken
            return False

    async def _listen(self) -> None:
        """Listen for incoming messages from the server."""
        while self.running and self.websocket:
            try:
                message_str = await asyncio.wait_for(self.websocket.recv(), timeout=None) # Listen indefinitely until closed
                message = json.loads(message_str)
                logger.debug(f"Received message type: {message.get('type')}")

                # Handle core message types or pass to handler
                if message.get("type") == "welcome":
                     logger.info(f"Registered successfully with server. Network size: {message.get('network_size')}")
                     # Perform initial state sync or other actions upon welcome
                elif message.get("type") == "error":
                     logger.error(f"Received error from server: {message.get('error')}")
                elif self.message_handler:
                    try:
                        self.message_handler(message)
                    except Exception as handler_e:
                        logger.error(f"Error in message handler: {handler_e}", exc_info=True)
                # else: No handler registered

            except websockets.exceptions.ConnectionClosedOK:
                logger.info("Server closed the connection normally.")
                break # Exit loop
            except websockets.exceptions.ConnectionClosedError as e:
                logger.warning(f"Connection closed with error: {e}")
                break # Exit loop
            except asyncio.TimeoutError:
                 logger.warning("WebSocket receive timeout (should not happen with timeout=None).")
                 # This indicates a potential issue with the connection or keepalive
                 await asyncio.sleep(1) # Wait before retrying receive
            except json.JSONDecodeError:
                logger.error("Received invalid JSON from server.")
            except Exception as e:
                logger.error(f"Error in listener loop: {e}", exc_info=True)
                break # Exit loop on unexpected errors

        # Connection lost or loop stopped
        logger.warning("Listener loop exited.")
        self.is_connected = False
        self.websocket = None


    async def _reconnect_task(self) -> None:
        """Task to handle automatic reconnection."""
        logger.info("Starting reconnection task.")
        current_delay = self.initial_reconnect_delay
        while self.running:
            if not self.is_connected:
                logger.info(f"Attempting reconnection (Attempt {self.reconnect_attempts + 1}/{self.max_reconnect_attempts})...")
                if await self.connect():
                    logger.info("Reconnection successful.")
                    # Restart listener if connection drops and loop exits
                    # (Assuming run() handles starting the listener initially)
                    asyncio.create_task(self._listen())
                    current_delay = self.initial_reconnect_delay # Reset delay
                else:
                    self.reconnect_attempts += 1
                    if self.reconnect_attempts >= self.max_reconnect_attempts:
                        logger.error("Max reconnection attempts reached. Stopping client.")
                        self.running = False
                        break # Exit reconnect loop
                    else:
                        wait_time = min(current_delay, self.max_reconnect_delay)
                        logger.info(f"Reconnection failed. Retrying in {wait_time:.1f} seconds...")
                        await asyncio.sleep(wait_time)
                        current_delay *= 1.5 # Exponential backoff
            else:
                 # Connected, wait before checking again
                 await asyncio.sleep(10) # Check connection status every 10 seconds

        logger.info("Reconnection task stopped.")


    async def run(self):
        """Connect to the server and start listening/reconnecting."""
        if self.running:
            logger.warning("Client is already running.")
            return

        self.running = True
        # Start the reconnection task which handles initial connection and listening
        reconnect_task = asyncio.create_task(self._reconnect_task())

        # Keep running until stopped
        try:
            await reconnect_task # Wait for reconnection task to finish (e.g., on max retries)
        except asyncio.CancelledError:
             logger.info("Run task cancelled.")
        finally:
             logger.info("Client run loop finished.")
             await self.close() # Ensure connection is closed on exit


    # --- Example Quantum Operations ---
    async def update_state_on_server(self):
        """Serialize local state and send to server."""
        if self.is_connected:
            await self.send_message({
                "type": "quantum_state_update",
                "state": self.state.serialize()
            })

    async def request_entanglement(self, target_node_id: str):
        """Request entanglement with another node."""
        if self.is_connected:
            await self.send_message({
                "type": "entanglement_request",
                "target_id": target_node_id
            })

    # Add more methods for interacting with the server...


# --- Main Execution (Example/Test) ---
async def run_client_example(config: Dict):
     """Example of running the client."""
     client = QuantumNetworkClient(config)

     def simple_handler(message: Dict):
          logger.info(f"Handler received message: {message.get('type')}")
          # Add logic to react to server messages (e.g., state updates, measurements)
          if message.get("type") == "some_server_action":
               asyncio.create_task(client.send_message({"type": "client_response"}))

     client.set_message_handler(simple_handler)

     run_task = asyncio.create_task(client.run())

     try:
          # Example interaction loop
          counter = 0
          while client.running and counter < 30: # Run for ~300 seconds
                await asyncio.sleep(10)
                if client.is_connected:
                     logger.info("Client sending keepalive ping...")
                     await client.send_message({"type": "ping"})
                     # Example: Update state periodically
                     # client.state.apply_noise(10)
                     # await client.update_state_on_server()
                counter += 1
          logger.info("Example interaction loop finished.")

     except asyncio.CancelledError:
          logger.info("Client example cancelled.")
     finally:
          await client.close()
          # Wait for run task to fully finish if needed
          await run_task

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kaleidoscope Quantum Network Client")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to the main config.json file")
    parser.add_argument("--node-id", help="Unique ID for this client node")
    parser.add_argument("--name", help="Name for this client node")
    parser.add_argument("--log", default="INFO", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="Logging level")
    args = parser.parse_args()

    # Setup logging level
    log_level_to_set = getattr(logging, args.log.upper(), logging.INFO)
    logging.basicConfig(level=log_level_to_set, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger.setLevel(log_level_to_set)

    # Load configuration
    config = load_configuration(Path(args.config))

    try:
        asyncio.run(run_client_example(config))
    except KeyboardInterrupt:
        logger.info("Client stopped by user.")
    except Exception as e:
         logger.critical(f"Client failed to run: {e}", exc_info=True)
         sys.exit(1)
    finally:
         logger.info("Exiting Quantum Client.")
