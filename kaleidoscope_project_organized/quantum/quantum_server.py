#!/usr/bin/env python3
"""
Quantum-Inspired Neural Network Synchronization System
Server Node Implementation
"""

import asyncio
import websockets
import numpy as np
import json
import logging
import time
import uuid
import networkx as nx
from scipy.sparse import csr_matrix
# from scipy.sparse.linalg import eigsh # Only needed if using specific sparse methods
from scipy.sparse.linalg import expm_multiply # Used in QuantumState.evolve
from collections import deque
import threading
from typing import Dict, List, Tuple, Set, Any, Optional, Union
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import signal
from pathlib import Path
import yaml # Needs PyYAML installed
import os # <-- IMPORT OS IS PRESENT HERE

# --- Configuration Management ---
@dataclass
class Config:
    """Server configuration settings"""
    host: str = "0.0.0.0"
    port: int = 8765
    hilbert_space_dim: int = 32
    entanglement_threshold: float = 0.75
    max_coherence_time: int = 120
    decoherence_rate: float = 0.05
    teleportation_probability: float = 0.3
    log_level: str = "INFO"
    max_nodes: int = 1000
    cleanup_interval: int = 30
    simulation_interval: float = 0.5
    max_message_size: int = 10 * 1024 * 1024  # 10MB

    def __post_init__(self):
        """Validate configuration values"""
        if not (0 <= self.entanglement_threshold <= 1):
            raise ValueError("entanglement_threshold must be between 0 and 1")
        if self.max_coherence_time < 0:
            raise ValueError("max_coherence_time cannot be negative")
        if self.decoherence_rate < 0:
            raise ValueError("decoherence_rate cannot be negative")
        if not (0 <= self.teleportation_probability <= 1):
            raise ValueError("teleportation_probability must be between 0 and 1")
        if self.port < 1024 or self.port > 65535: # Use common port range
            raise ValueError("port must be between 1024 and 65535")
        if self.hilbert_space_dim <= 0:
            raise ValueError("hilbert_space_dim must be positive")
        if self.max_nodes <= 0:
            raise ValueError("max_nodes must be positive")

    @classmethod
    def from_config_data(cls, config_data: Dict[str, Any]) -> 'Config':
        """Create Config object from a dictionary, applying defaults for missing keys."""
        valid_keys = {f.name for f in field(cls) if f.init}
        filtered_data = {k: v for k, v in config_data.items() if k in valid_keys}
        try:
             instance = cls(**filtered_data)
             instance.__post_init__() # Manually call validation
             return instance
        except Exception as e:
             logger.error(f"Failed to create valid Config object: {e}. Using defaults.", exc_info=True)
             return cls() # Return default config on error

# --- Logging Setup ---
logger = logging.getLogger("quantum-server")
# Config object needs to be created after parsing args in main
CONFIG = Config() # Initial default config

class QuantumState:
    """Represents a quantum state with optimized operations"""

    def __init__(self, dimension: int = CONFIG.hilbert_space_dim):
        self.dimension = dimension
        self.state = self._init_state()
        self.creation_time = time.time()
        self.fidelity = 1.0
        self.entangled_with: Set[str] = set()

    def _init_state(self) -> np.ndarray:
        """Initialize a random pure state"""
        rng = np.random.default_rng(int(time.time_ns() % (2**32)))
        state_real = rng.normal(0, 1, self.dimension)
        state_imag = rng.normal(0, 1, self.dimension)
        state = state_real + 1j * state_imag
        norm = np.linalg.norm(state)
        return state / norm if norm > 1e-15 else self._init_state() # Avoid division by zero

    def evolve(self, hamiltonian: csr_matrix, dt: float) -> None:
        """Evolve quantum state using sparse matrix operations"""
        try:
            if not isinstance(hamiltonian, csr_matrix):
                 hamiltonian = csr_matrix(hamiltonian)
            self.state = expm_multiply(-1j * hamiltonian * dt, self.state)
            norm = np.linalg.norm(self.state)
            if norm > 1e-15:
                self.state /= norm
            else: # Renormalize or reinitialize if norm is too small
                 logger.warning("State vector norm too small after evolution, reinitializing.")
                 self.state = self._init_state()
                 self.fidelity = 0.0 # Reset fidelity as state is new
        except ImportError:
             logger.warning("scipy.sparse.linalg.expm_multiply not available. State evolution skipped.")
             self.fidelity *= 0.99
        except Exception as e:
            logger.error(f"State evolution failed: {e}", exc_info=True)
            self.fidelity *= 0.9

    def apply_noise(self, dt: float) -> None:
        """Apply decoherence noise efficiently"""
        elapsed = time.time() - self.creation_time
        if elapsed > CONFIG.max_coherence_time or self.fidelity <= 0:
            self.fidelity = 0.0
            return
        decoherence = max(0.0, min(1.0, np.exp(-CONFIG.decoherence_rate * elapsed)))
        if decoherence < 1.0:
            rng = np.random.default_rng()
            noise_real = rng.normal(0, 1, self.dimension)
            noise_imag = rng.normal(0, 1, self.dimension)
            noise = noise_real + 1j * noise_imag
            noise_norm = np.linalg.norm(noise)
            noise = noise / noise_norm if noise_norm > 1e-15 else self._init_state() # Use normalized noise
            mix_factor_sq = max(0.0, 1.0 - decoherence**2)
            mix_factor = np.sqrt(mix_factor_sq)
            self.state = decoherence * self.state + mix_factor * noise
            norm = np.linalg.norm(self.state)
            if norm > 1e-15:
                 self.state /= norm
            else:
                 logger.warning("State vector norm too small after noise, reinitializing.")
                 self.state = self._init_state()
                 self.fidelity = 0.0 # Reset fidelity
                 return # Exit early as state is new
            self.fidelity = decoherence

    def measure(self, observable: csr_matrix) -> float:
        """Measure an observable with error checking"""
        try:
            if not isinstance(observable, csr_matrix):
                observable = csr_matrix(observable)
            op_psi = observable @ self.state
            expectation = np.vdot(self.state, op_psi)
            return float(np.real(expectation))
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Measurement failed: {e}", exc_info=True)
            return 0.0

    def entangle_with(self, other_id: str) -> None:
        self.entangled_with.add(other_id)

    def serialize(self) -> Dict[str, Any]:
        real_list = self.state.real.astype(np.float32).tolist()
        imag_list = self.state.imag.astype(np.float32).tolist()
        return {
            "real": real_list, "imag": imag_list,
            "fidelity": float(self.fidelity),
            "creation_time": self.creation_time,
            "entangled_with": list(self.entangled_with)
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'QuantumState':
        try:
            dim = len(data["real"])
            if dim == 0: raise ValueError("State data has zero dimension")
            state = cls(dimension=dim)
            state.state = np.array(data["real"], dtype=np.float32) + 1j * np.array(data["imag"], dtype=np.float32)
            norm = np.linalg.norm(state.state)
            if norm > 1e-10: state.state /= norm
            else:
                logger.warning("Deserialized zero state vector, reinitializing.")
                state.state = state._init_state()
            state.fidelity = data.get("fidelity", 1.0)
            state.creation_time = data.get("creation_time", time.time())
            state.entangled_with = set(data.get("entangled_with", []))
            return state
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"QuantumState Deserialization failed: {e}", exc_info=True)
            return cls(dimension=CONFIG.hilbert_space_dim) # Return default on error


@dataclass
class QuantumNetworkNode:
    id: str
    name: str
    state: QuantumState = field(default_factory=lambda: QuantumState(dimension=CONFIG.hilbert_space_dim))
    connection: Optional[websockets.WebSocketServerProtocol] = None
    is_active: bool = True
    creation_time: float = field(default_factory=time.time)
    last_interaction: float = field(default_factory=time.time)
    metrics: Dict[str, int] = field(default_factory=lambda: {
        "processed_messages": 0, "quantum_operations": 0,
        "entanglement_count": 0, "teleportation_attempts": 0,
        "teleportation_successes": 0
    })
    capabilities: Set[str] = field(default_factory=set)

    def update_activity(self) -> None:
        self.last_interaction = time.time()

    def is_stale(self) -> bool:
        return (time.time() - self.last_interaction) > (CONFIG.cleanup_interval * 2)


class QuantumNetworkServer:
    """Enhanced WebSocket server for quantum network management"""

    def __init__(self, config: Config):
        self.config = config
        self.host = config.host
        self.port = config.port
        self.nodes: Dict[str, QuantumNetworkNode] = {}
        self.connections: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.network_graph = nx.Graph()
        self.global_state = QuantumState(dimension=config.hilbert_space_dim)
        self.observables = self._generate_observables()
        self.shutdown_event = asyncio.Event()
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count() or 4)
        self.lock = threading.Lock() # Use threading lock
        self.metrics = {
            "total_connections_handled": 0, "active_nodes": 0,
            "failed_operations": 0, "messages_processed": 0,
        }

    def _generate_observables(self) -> Dict[str, csr_matrix]:
        dim = self.config.hilbert_space_dim
        observables = {}
        rng = np.random.default_rng()
        logger.debug(f"Generating observables for dimension {dim}")
        for name in ["Energy", "Momentum", "Position", "Global"]:
             try:
                  mat_real = rng.normal(0, 1, (dim, dim))
                  mat_imag = rng.normal(0, 1, (dim, dim))
                  mat = mat_real + 1j * mat_imag
                  mat = (mat + mat.conj().T) / 2 # Make Hermitian
                  observables[name] = csr_matrix(mat)
             except Exception as e:
                  logger.error(f"Failed to generate observable '{name}': {e}", exc_info=True)
                  observables[name] = csr_matrix((dim, dim), dtype=complex) # Fallback
        logger.debug(f"Generated {len(observables)} observables.")
        return observables

    def register_node(self, node_id: str, name: str, connection: websockets.WebSocketServerProtocol) -> QuantumNetworkNode:
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                old_conn = node.connection
                if old_conn and old_conn in self.connections and self.connections[old_conn] == node_id:
                     del self.connections[old_conn]
                     logger.debug(f"Cleaned up old connection map for re-registering node {node_id}")
                node.connection = connection
                node.is_active = True
                node.update_activity()
                logger.info(f"Node re-registered and activated: {name} ({node_id})")
            else:
                if len(self.nodes) >= self.config.max_nodes:
                     logger.warning(f"Max node limit ({self.config.max_nodes}) reached. Rejecting new node: {name} ({node_id})")
                     raise ConnectionRefusedError(f"Maximum node limit ({self.config.max_nodes}) reached")
                node = QuantumNetworkNode(node_id, name)
                node.connection = connection
                self.nodes[node_id] = node
                if not self.network_graph.has_node(node_id):
                     self.network_graph.add_node(node_id, name=name, active=True)
                logger.info(f"Node registered: {name} ({node_id})")

            self.connections[connection] = node_id
            self.metrics["total_connections_handled"] += 1
            self.metrics["active_nodes"] = sum(1 for n in self.nodes.values() if n.is_active)
            return node

    def remove_node(self, node_id: str) -> None:
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node.is_active = False
                connection = node.connection
                if connection and connection in self.connections:
                    del self.connections[connection]
                    node.connection = None

                # Keep inactive node data for potential later analysis? Or delete?
                # Let's delete fully for now to prevent memory leak
                if self.network_graph.has_node(node_id):
                     try: self.network_graph.remove_node(node_id)
                     except Exception as e: logger.warning(f"Error removing node {node_id} from graph: {e}")
                del self.nodes[node_id] # Delete from main dictionary

                self.metrics["active_nodes"] = sum(1 for n in self.nodes.values() if n.is_active)
                logger.info(f"Node removed: {node.name} ({node_id})")
            else:
                 logger.debug(f"Attempted to remove non-existent node: {node_id}")


    # (Rest of QuantumNetworkServer methods like broadcast, calculate_entanglement,
    #  update_network_graph, create_hamiltonian, process_message, simulation_loop,
    #  cleanup_loop need to be included here, preferably the enhanced versions from
    #  the previous response where error handling and locking were improved)

    # --- handle_connection with Corrected Syntax and Enhanced Error Logging ---
    async def handle_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle a WebSocket connection with robust error handling"""
        node_id = f"pending_{uuid.uuid4().hex[:6]}" # Default ID before registration
        node_name = "Unknown"
        remote_addr = websocket.remote_address
        node = None
        logger.info(f"New connection attempt from {remote_addr}")
        try:
            websocket.max_size = self.config.max_message_size

            # Registration phase with timeout
            init_message_str = await asyncio.wait_for(websocket.recv(), timeout=15.0)
            init_data = json.loads(init_message_str)

            if init_data.get("type") != "register":
                raise ValueError("First message must be registration type 'register'")

            # Use provided ID or generate one
            node_id = init_data.get("node_id") or f"node_{uuid.uuid4().hex[:8]}"
            node_name = init_data.get("name") or f"Node-{node_id[:8]}"

            # Try to register node, handle potential rejection (e.g., max nodes)
            node = self.register_node(node_id, node_name, websocket) # Raises ConnectionRefusedError if fails

            # Send welcome message
            await websocket.send(json.dumps({
                "type": "welcome", "node_id": node_id,
                "network_size": len(self.nodes),
                "active_nodes": self.metrics["active_nodes"],
                "global_state_fidelity": self.global_state.fidelity
            }))
            logger.info(f"Connection established for {node_name} ({node_id}) from {remote_addr}")

            # Main message processing loop
            async for message_str in websocket:
                try:
                    # Basic message size check early if needed, though websockets handles max_size
                    data = json.loads(message_str)
                    response = await self.process_message(node_id, data) # process_message handles its own errors
                    if response:
                        response_json = json.dumps(response)
                        if len(response_json.encode('utf-8')) > self.config.max_message_size:
                              logger.error(f"Response message too large for node {node_id}")
                              await websocket.send(json.dumps({"type": "error", "error": "Response too large"}))
                        else:
                              await asyncio.wait_for(websocket.send(response_json), timeout=WEBSOCKET_TIMEOUT)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from {node_name} ({node_id})")
                    await websocket.send(json.dumps({"type": "error", "error": "Invalid JSON format"}))
                except asyncio.TimeoutError:
                     logger.error(f"Timeout sending response to {node_name} ({node_id})")
                     # Consider closing connection after repeated send timeouts
                except Exception as msg_proc_e:
                    logger.error(f"Error processing message loop for {node_name} ({node_id}): {msg_proc_e}", exc_info=True)
                    try: # Attempt to notify client of error
                         await websocket.send(json.dumps({"type": "error", "error": f"Internal error: {str(msg_proc_e)}"}))
                    except Exception: pass # Ignore if send fails

        # Handle specific disconnection reasons
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"Connection closed normally for {node_name} ({node_id})")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"Connection closed with error for {node_name} ({node_id}): {e}")
        except asyncio.TimeoutError:
             logger.warning(f"Timeout waiting for registration from {remote_addr}. Closing connection.")
        except json.JSONDecodeError:
             logger.warning(f"Invalid JSON during registration from {remote_addr}. Closing connection.")
        except ValueError as e: # Catch validation errors like bad registration message
             logger.warning(f"Connection rejected for {remote_addr}: {e}")
             if websocket and not websocket.closed:
                  await websocket.send(json.dumps({"type": "error", "error": str(e)}))
        except ConnectionRefusedError as e: # Catch registration rejection
              logger.warning(f"Registration refused for {node_name} ({node_id}): {e}")
              # Error message already sent in register_node
        except Exception as e: # Catch other unexpected errors
            logger.error(f"Unexpected error in connection handler for {node_name} ({node_id}): {e}", exc_info=True)
            if websocket and not websocket.closed:
                 try: await websocket.send(json.dumps({"type": "error", "error": "Unexpected server error"}))
                 except Exception: pass

        finally:
            logger.debug(f"Cleaning up connection: {remote_addr}, Node ID: {node_id}")
            self.remove_node(node_id) # remove_node handles locking and checks existence
            if websocket and not websocket.closed:
                try:
                    await websocket.close(code=1001, reason="Server cleaning up")
                except Exception as close_e:
                    logger.debug(f"Error during websocket close for {node_name}: {close_e}")


    async def run(self) -> None:
        """Start the WebSocket server and background tasks"""
        logger.info(f"Starting Quantum Network Server on {self.host}:{self.port}")
        logger.info(f"Using Configuration: {self.config}")
        # Create tasks within the run method after event loop is running
        sim_task = asyncio.create_task(self.simulation_loop())
        clean_task = asyncio.create_task(self.cleanup_loop())
        self.tasks = {sim_task, clean_task} # Store tasks for cancellation

        server_instance = None
        try:
            server_instance = await websockets.serve(
                self.handle_connection, self.host, self.port,
                max_size=self.config.max_message_size,
                ping_interval=20, ping_timeout=20 # Add keepalive
            )
            logger.info(f"Server listening on ws://{self.host}:{self.port}")
            await self.shutdown_event.wait()

        except OSError as e:
             logger.critical(f"Failed to start server on {self.host}:{self.port} - {e}.", exc_info=True)
             self.shutdown_event.set()
        except Exception as e:
             logger.critical(f"Server runtime error: {e}", exc_info=True)
             self.shutdown_event.set()
        finally:
            logger.info("Server shutting down...")
            if server_instance:
                 server_instance.close()
                 try: await asyncio.wait_for(server_instance.wait_closed(), timeout=5.0)
                 except asyncio.TimeoutError: logger.warning("Timeout waiting for WebSocket server to close.")
                 logger.info("WebSocket server stopped.")

            logger.info("Stopping background tasks...")
            for task in self.tasks:
                 if task and not task.done(): task.cancel()
            await asyncio.gather(*self.tasks, return_exceptions=True) # Wait for tasks
            self.executor.shutdown(wait=True) # Shutdown threadpool cleanly
            logger.info("Background tasks stopped.")
            logger.info("Shutdown complete.")

    def shutdown(self) -> None:
        """Initiate server shutdown"""
        if not self.shutdown_event.is_set():
             logger.info("Shutdown signal received.")
             self.shutdown_event.set()

# --- Main Execution ---
async def main(config_obj: Config) -> None: # Accept Config object
    server = QuantumNetworkServer(config_obj)

    # Setup signal handlers more robustly
    loop = asyncio.get_running_loop()
    def _shutdown_signal_handler(sig):
         logger.info(f"Received signal {sig.name}, initiating shutdown...")
         # Use call_soon_threadsafe if shutdown might be called from another thread
         # loop.call_soon_threadsafe(server.shutdown)
         # If running purely in asyncio, call directly
         if not server.shutdown_event.is_set():
              server.shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
             loop.add_signal_handler(sig, _shutdown_signal_handler, sig)
        except NotImplementedError: # Windows compatibility
             logger.warning(f"Cannot set signal handler for {sig} on this platform.")

    await server.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum Network Server v3.7")
    # Change default config to config.json? Or keep YAML? Let's assume YAML for this file.
    parser.add_argument("--config", default="quantum_config.yaml", help="Path to YAML configuration file")
    parser.add_argument("--host", help="Host to bind the server to (overrides config)")
    parser.add_argument("--port", type=int, help="Port to listen on (overrides config)")
    parser.add_argument("--log", help="Logging level (overrides config)")
    args = parser.parse_args()

    # --- Load Config ---
    try:
         # Load YAML config using the Config class method
         config = Config.from_file(args.config)
    except Exception as e:
         # Basic logging setup for config loading error
         logging.basicConfig(level="ERROR")
         logger = logging.getLogger("QuantumServerInit")
         logger.critical(f"Failed to initialize configuration from {args.config}: {e}. Exiting.", exc_info=True)
         sys.exit(1)

    # Override with command-line arguments if provided
    if args.host: config.host = args.host
    if args.port: config.port = args.port
    if args.log: config.log_level = args.log.upper()

    # --- Setup logging based on final config ---
    try:
        log_level_to_set = getattr(logging, config.log_level, logging.INFO)
        log_format = '%(asctime)s [%(levelname)-8s] %(name)s: %(message)s'
        log_datefmt = '%Y-%m-%d %H:%M:%S'
        log_file_path = Path(f"quantum_server_{config.port}.log") # Log file based on port

        handlers = [logging.StreamHandler(sys.stdout)]
        try:
             # Use file handler with rotation? Basic for now.
             file_handler = logging.FileHandler(log_file_path)
             file_handler.setFormatter(logging.Formatter(log_format, datefmt=log_datefmt))
             handlers.append(file_handler)
        except Exception as e:
             print(f"Warning: Could not configure file logging to {log_file_path}: {e}", file=sys.stderr)

        # Configure root logger
        logging.basicConfig(level=log_level_to_set,
                             format=log_format,
                             datefmt=log_datefmt,
                             handlers=handlers,
                             force=True) # Force reconfig if already configured

        # Set level for this module's logger specifically too
        logging.getLogger("quantum-server").setLevel(log_level_to_set)
        # Silence overly verbose libraries if needed
        logging.getLogger("websockets").setLevel(logging.INFO)

    except Exception as e:
        print(f"Error configuring logging: {e}", file=sys.stderr)
        # Continue with default logging

    # --- Run Server ---
    try:
        # Pass the validated Config object
        asyncio.run(main(config))
    except KeyboardInterrupt:
        logger.info("Server stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Server failed to run: {e}", exc_info=True)
        sys.exit(1)
    finally:
         logger.info("Exiting Quantum Server.")
