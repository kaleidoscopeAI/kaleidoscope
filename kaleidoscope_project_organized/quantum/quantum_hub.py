#!/usr/bin/env python3
"""
Quantum Kaleidoscope Orchestration Hub (v2)
===========================================
Middleware integrating the Quantum Kaleidoscope backend (SuperNodeCore)
with visualization frontends via Flask and SocketIO. Aligned with core system standards.

Usage:
    python quantum/quantum_hub.py [--port <port>] [--config <path>] [--data-dir <path>]

Requirements:
    - Flask, Flask-SocketIO, numpy, networkx, python-dotenv, eventlet, PyYAML
    - supernode_core.py (or access to the SuperNodeCore class)
"""

import os
import sys
import time
import json
import uuid
import math
import argparse
import threading
import random
import logging
from pathlib import Path
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

# --- Import Dependencies ---
try:
    from flask import Flask, send_file, request
    from flask_socketio import SocketIO, emit
    import networkx as nx
    import eventlet # Required by Flask-SocketIO for async mode
    eventlet.monkey_patch() # Patch standard libraries for eventlet compatibility
except ImportError as e:
    print(f"Required package missing: {e}")
    print("Please install: pip install flask flask-socketio numpy networkx python-dotenv eventlet PyYAML")
    sys.exit(1)

# --- Import Core Components ---
# Assuming SuperNodeCore is accessible via the installed package structure
try:
    from supernode.supernode_core import SuperNodeCore, encode_data, decode_data
except ImportError:
    print("Error: Cannot import SuperNodeCore. Ensure project is installed ('pip install -e .') and venv active.")
    # Add fallback path logic if needed for direct execution (less ideal)
    # SCRIPT_DIR = Path(__file__).resolve().parent
    # PROJECT_ROOT = SCRIPT_DIR.parent
    # if str(PROJECT_ROOT) not in sys.path: sys.path.append(str(PROJECT_ROOT))
    # try: from supernode.supernode_core import SuperNodeCore, encode_data, decode_data
    # except ImportError: sys.exit("SuperNodeCore not found.")
    sys.exit(1)


# --- Configuration Loading ---
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json" # Assumes config.json in project root

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
# If run standalone, basicConfig might be needed here.
logger = logging.getLogger("QuantumHub")

# --- Data Structures (Same as before, ensure consistency if shared) ---
@dataclass
class QuantumNode:
    id: str
    position: Tuple[float, float, float]
    energy: float
    stability: float
    connections: Dict[str, float] = field(default_factory=dict)
    features: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    visible: bool = True
    creation_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    color: str = "#4488ff"
    size: float = 1.0

    def to_dict(self) -> Dict:
        # Limit features sent to frontend
        metadata_preview = {k: str(v)[:50] + ('...' if len(str(v)) > 50 else '') for k, v in self.metadata.items()}
        return {
            "id": self.id, "position": list(self.position), "energy": self.energy, "stability": self.stability,
            "connections": self.connections, "features": self.features[:10], # Send fewer features
            "metadata": metadata_preview, "visible": self.visible,
            "creation_time": self.creation_time, "last_update": self.last_update,
            "color": self.color, "size": self.size
        }

@dataclass
class QuantumConnection:
    source: str
    target: str
    strength: float = 0.5
    type: str = "standard"
    metadata: Dict[str, Any] = field(default_factory=dict)
    visible: bool = True
    creation_time: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "source": self.source, "target": self.target, "strength": self.strength, "type": self.type,
            "metadata": self.metadata, "visible": self.visible, "creation_time": self.creation_time
        }

@dataclass
class SimulationState:
    nodes: Dict[str, QuantumNode] = field(default_factory=dict)
    connections: List[QuantumConnection] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list) # Consider capping size
    insights: List[Dict[str, Any]] = field(default_factory=list) # Consider capping size
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    MAX_EVENTS = 100
    MAX_INSIGHTS = 50

    def add_event(self, event: Dict[str, Any]):
        self.events.append(event)
        # Limit history size
        if len(self.events) > self.MAX_EVENTS:
            self.events.pop(0)

    def add_insight(self, insight: Dict[str, Any]):
         self.insights.append(insight)
         if len(self.insights) > self.MAX_INSIGHTS:
              self.insights.pop(0)

    def to_dict(self) -> Dict:
        return {
            "nodes": [node.to_dict() for node in self.nodes.values() if node.visible], # Only send visible nodes
            "connections": [conn.to_dict() for conn in self.connections if conn.visible], # Only send visible connections
            "events": self.events, "insights": self.insights, "metrics": self.metrics,
            "timestamp": self.timestamp
        }


class QuantumOrchestrator:
    """Manages the simulation state and interacts with SuperNodeCore."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the orchestrator.

        Args:
            config (Dict[str, Any]): Loaded configuration dictionary.
        """
        self.config = config
        self.paths_config = config.get("paths", {})
        self.data_dir = Path(self.paths_config.get("data_dir", "./data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.state = SimulationState()
        self.state_lock = threading.RLock() # Reentrant lock for complex state updates
        self.running = True
        self.simulation_thread = None
        self.network_graph = nx.Graph()
        self.metrics = {"fps": 0, "node_count": 0, "connection_count": 0, "update_time_ms": 0, "start_time": time.time()}

        # Initialize SuperNodeCore
        try:
            # Pass config relevant to SuperNodeCore if its init accepts it
            self.supernode = SuperNodeCore(config=config) # Assuming SuperNodeCore accepts config
            self.supernode.start()
            self._initialize_from_supernode()
            logger.info("SuperNodeCore initialized and started.")
        except Exception as e:
            logger.critical(f"Failed to initialize SuperNodeCore: {e}", exc_info=True)
            # Decide how to handle this - maybe run without supernode features?
            self.supernode = None
            # raise # Or re-raise to stop hub startup

    def _initialize_from_supernode(self):
        """Initialize visualization state based on SuperNodeCore."""
        if not self.supernode: return
        logger.info("Initializing visualization state from SuperNodeCore")
        try:
            # Create a representation for the SuperNode itself
            seed_node = QuantumNode(
                id=self.supernode.id,
                position=(0, 0, 0), # Center position
                energy=self.supernode.state.energy,
                stability=self.supernode.state.stability,
                features=self.supernode.state.vector[:32].tolist(), # Example: first 32 features
                metadata={"type": "supernode_core", "description": "Origin SuperNode"}
            )
            with self.state_lock:
                self.state.nodes[seed_node.id] = seed_node
                self.state.add_event({"type": "system", "message": "Initialized from SuperNode", "timestamp": time.time()})
                self._update_metrics() # Update initial metrics
        except Exception as e:
            logger.error(f"Failed to initialize state from SuperNode: {e}", exc_info=True)

    def start(self):
        """Start the orchestrator's simulation loop."""
        if self.simulation_thread and self.simulation_thread.is_alive():
            logger.warning("Simulation loop already running.")
            return
        logger.info("Starting Quantum Orchestrator simulation loop")
        self.running = True
        self.simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.simulation_thread.start()

    def stop(self):
        """Stop the orchestrator and SuperNode."""
        logger.info("Stopping Quantum Orchestrator")
        self.running = False
        if self.supernode:
            try:
                self.supernode.stop()
            except Exception as e:
                 logger.error(f"Error stopping SuperNodeCore: {e}", exc_info=True)
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=2.0)
        logger.info("Quantum Orchestrator stopped.")

    def get_current_state(self) -> Dict[str, Any]:
        """Get the current simulation state safely."""
        with self.state_lock:
            return self.state.to_dict()

    def process_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Process text input using SuperNodeCore and update visualization state."""
        if not self.supernode:
            logger.warning("SuperNodeCore not available for text processing.")
            return None
        if not text or not isinstance(text, str):
            logger.warning("Invalid text input received.")
            return None

        if not metadata: metadata = {}
        metadata.update({"timestamp": time.time(), "source": "user_input", "text_sample": text[:100] + ("..." if len(text) > 100 else "")})
        logger.info(f"Processing text input ({len(text)} characters)")

        try:
            # Process text with SuperNodeCore
            # Run potentially blocking call in executor if process_text is slow
            loop = asyncio.get_event_loop()
            output, resonance = loop.run_until_complete(
                 loop.run_in_executor(self.executor, self.supernode.process_text, text)
            )
            # output, resonance = self.supernode.process_text(text) # If process_text is fast/non-blocking

            decoded = decode_data(output) # Assuming decode_data is available

            with self.state_lock:
                node_id = f"text_node_{uuid.uuid4().hex[:6]}"
                # Determine position based on some feature or randomly
                # Example: Use first 3 features from output vector if available
                pos_features = output[:3] if len(output) >= 3 else [random.uniform(-1,1) for _ in range(3)]
                position = tuple(p * 15 for p in pos_features) # Scale position

                node = QuantumNode(
                    id=node_id,
                    position=position,
                    energy=resonance, # Use resonance as energy proxy
                    stability=self.supernode.state.stability, # Or derive from resonance?
                    features=output[:32].tolist(), # Store some output features
                    metadata=metadata,
                    color=self._generate_color_from_text(text)
                )
                self.state.nodes[node_id] = node

                # Connect to seed node if similarity is high
                seed_node = self.state.nodes.get(self.supernode.id)
                similarity = 0
                if seed_node:
                    similarity = self._calculate_similarity(seed_node.features, node.features)
                    if similarity > 0.5: # Lower threshold?
                        conn = QuantumConnection(source=seed_node.id, target=node_id, strength=similarity, type="semantic")
                        self.state.connections.append(conn)
                        # Update connection lists on nodes
                        seed_node.connections[node_id] = similarity
                        node.connections[seed_node.id] = similarity

                # Generate insights
                insights = self._generate_insights_from_text(text, node_id, [(seed_node.id, similarity)] if seed_node and similarity > 0.5 else [])
                for insight in insights: self.state.add_insight(insight)
                self.state.add_event({"type": "node_creation", "node_id": node_id, "message": "Created node from text", "timestamp": time.time()})
                self.state.timestamp = time.time()
                self._update_metrics() # Update metrics after adding node

            logger.info(f"Text processed. New node: {node_id}, Resonance: {resonance:.3f}")
            return {"node_id": node_id, "position": list(position), "decoded": decoded, "resonance": resonance, "insights": insights}

        except Exception as e:
            logger.error(f"Error processing text: {e}", exc_info=True)
            with self.state_lock:
                self.state.add_event({"type": "error", "message": f"Text processing failed: {e}", "timestamp": time.time()})
            return None

    def _calculate_similarity(self, features1: List[float], features2: List[float]) -> float:
        """Calculate cosine similarity between feature vectors."""
        if not features1 or not features2: return 0.0
        vec1 = np.array(features1)
        vec2 = np.array(features2)
        # Ensure vectors have same length for dot product (pad if necessary)
        len1, len2 = len(vec1), len(vec2)
        if len1 > len2: vec2 = np.pad(vec2, (0, len1 - len2))
        elif len2 > len1: vec1 = np.pad(vec1, (0, len2 - len1))

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0: return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def _generate_color_from_text(self, text: str) -> str:
        """Generate a deterministic color based on text hash."""
        import hashlib
        try:
            hash_val = int(hashlib.md5(text.encode('utf-8', errors='ignore')).hexdigest(), 16)
            # Use hash to generate hue, keep saturation/lightness reasonable
            hue = (hash_val % 360) / 360.0
            saturation = 0.6 + (hash_val % 40) / 100.0 # 0.6 - 1.0
            lightness = 0.5 + (hash_val % 30) / 100.0 # 0.5 - 0.8
            # Convert HSL to RGB hex (implementation needed or use library like 'colorsys')
            # Simplified placeholder: use hash directly
            hex_color = "#" + hashlib.md5(text.encode('utf-8')).hexdigest()[:6]
            return hex_color
        except Exception:
             return "#808080" # Default gray on error

    def _generate_insights_from_text(self, text: str, node_id: str, related_nodes: List[Tuple[str, float]]) -> List[Dict[str, Any]]:
        """Generate basic insights based on text properties."""
        words = text.lower().split()
        word_count = len(words)
        avg_word_len = sum(len(w) for w in words) / max(1, word_count)
        complexity = min(1.0, avg_word_len / 7.0) # Normalize complexity guess
        insights = [{
            "type": "content_analysis", "title": "Text Metrics",
            "content": f"Input: {word_count} words, Avg Len: {avg_word_len:.1f}, Complexity: {complexity:.2f}",
            "confidence": 0.8, "timestamp": time.time(), "node_id": node_id
        }]
        if related_nodes:
            top_id, similarity = related_nodes[0]
            insights.append({
                "type": "relationship", "title": "Semantic Link",
                "content": f"Node {node_id[:6]} linked to {top_id[:6]} (Sim: {similarity:.2f})",
                "confidence": similarity, "timestamp": time.time(), "nodes": [node_id, top_id]
            })
        return insights

    def _update_metrics(self):
        """Update overall simulation metrics."""
        # Assumes called within state_lock
        num_nodes = len(self.state.nodes)
        num_connections = len(self.state.connections)
        avg_energy = np.mean([n.energy for n in self.state.nodes.values()]) if num_nodes > 0 else 0
        avg_conns_per_node = np.mean([len(n.connections) for n in self.state.nodes.values()]) if num_nodes > 0 else 0

        self.state.metrics.update({
            "node_count": num_nodes,
            "connection_count": num_connections,
            "avg_energy": avg_energy,
            "avg_connections": avg_conns_per_node,
            "simulation_time": time.time() - self.metrics["start_time"]
        })
        # Update top-level metrics for quick access
        self.metrics.update(self.state.metrics)


    def _simulation_loop(self):
        """Main simulation loop for updating node positions and states."""
        logger.info("Starting Hub simulation loop")
        last_metrics_update = time.time()
        frame_count = 0

        while self.running:
            start_time = time.time()
            try:
                with self.state_lock:
                    # 1. Update seed node from SuperNodeCore
                    if self.supernode and self.supernode.id in self.state.nodes:
                        seed_node = self.state.nodes[self.supernode.id]
                        seed_node.energy = self.supernode.state.energy
                        seed_node.stability = self.supernode.state.stability
                        seed_node.features = self.supernode.state.vector[:32].tolist()
                        seed_node.last_update = time.time()

                    # 2. Apply simplified force-directed layout (can be slow for many nodes)
                    if len(self.state.nodes) > 1:
                         # Run layout less frequently? Or use faster algorithm?
                         positions = self._calculate_layout()
                         for node_id, pos in positions.items():
                              if node_id in self.state.nodes:
                                   self.state.nodes[node_id].position = pos

                    # 3. Simple node property updates (e.g., decay energy, check visibility)
                    nodes_to_prune = []
                    current_time = time.time()
                    for node_id, node in self.state.nodes.items():
                         if node_id != self.supernode.id: # Don't decay supernode representation
                              node.energy *= 0.995 # Slow energy decay
                              node.stability = max(0.1, node.stability * 0.998) # Stability decay
                              if node.energy < 0.05:
                                   node.visible = False # Hide low energy nodes
                                   if current_time - node.creation_time > 300: # Prune old invisible nodes
                                        nodes_to_prune.append(node_id)
                         node.last_update = current_time

                    # Prune nodes outside lock iteration
                    if nodes_to_prune:
                         logger.info(f"Pruning {len(nodes_to_prune)} low-energy/old nodes.")
                         for node_id in nodes_to_prune:
                              if node_id in self.state.nodes: del self.state.nodes[node_id]
                              # Also remove associated connections
                              self.state.connections = [
                                   conn for conn in self.state.connections
                                   if conn.source != node_id and conn.target != node_id
                              ]


                    # 4. Update metrics
                    self._update_metrics()
                    self.state.timestamp = current_time

                # --- End of state_lock block ---

                # Update FPS counter
                frame_count += 1
                now = time.time()
                if now - last_metrics_update >= 1.0:
                    self.metrics["fps"] = frame_count / (now - last_metrics_update)
                    self.metrics["update_time_ms"] = (now - start_time) * 1000 / frame_count if frame_count > 0 else 0
                    logger.debug(f"FPS: {self.metrics['fps']:.1f}, Update Time: {self.metrics['update_time_ms']:.1f} ms")
                    frame_count = 0
                    last_metrics_update = now

                # Control loop speed (~30 FPS target)
                elapsed = time.time() - start_time
                sleep_duration = max(0, 0.033 - elapsed)
                time.sleep(sleep_duration) # Use time.sleep for threaded loop

            except Exception as e:
                logger.error(f"Error in simulation loop: {e}", exc_info=True)
                time.sleep(1) # Avoid tight loop on error

        logger.info("Simulation loop stopped.")

    def _calculate_layout(self) -> Dict[str, Tuple[float, float, float]]:
         """Calculates node positions using NetworkX spring layout."""
         # Assumes called within state_lock or graph is consistent
         if len(self.state.nodes) < 2:
              return {nid: n.position for nid, n in self.state.nodes.items()}

         # Build graph for layout
         G = nx.Graph()
         node_list = list(self.state.nodes.keys())
         G.add_nodes_from(node_list)
         edges_for_layout = [(c.source, c.target, {"weight": 1.0 - c.strength}) for c in self.state.connections if c.source in node_list and c.target in node_list]
         G.add_edges_from(edges_for_layout)

         # Get initial positions to seed layout
         initial_pos = {nid: self.state.nodes[nid].position[:2] for nid in node_list} # Use X,Y only for 2D layout

         try:
              # Use networkx spring layout (can be slow)
              # Consider using faster alternatives or reducing iterations for large graphs
              pos_2d = nx.spring_layout(G, pos=initial_pos, k=0.8/math.sqrt(len(node_list)) if len(node_list)>0 else 0.8, iterations=15, dim=2, weight='weight')

              # Convert back to 3D, using Z based on energy or keeping original Z?
              # Let's try mapping energy to Z, scaled
              min_e = min(n.energy for n in self.state.nodes.values())
              max_e = max(n.energy for n in self.state.nodes.values())
              range_e = max(max_e - min_e, 1e-6)
              scale = 10.0 # Z-scale

              pos_3d = {}
              for node_id, (x, y) in pos_2d.items():
                   energy_norm = (self.state.nodes[node_id].energy - min_e) / range_e
                   z = (energy_norm - 0.5) * scale # Center around z=0
                   pos_3d[node_id] = (x*20, y*20, z) # Scale XY layout too

              return pos_3d

         except Exception as e:
              logger.error(f"Layout calculation failed: {e}", exc_info=True)
              # Return current positions on failure
              return {nid: n.position for nid, n in self.state.nodes.items()}


# --- Flask Server with SocketIO Integration ---
class QuantumKaleidoscopeServer:
    """Integrates Orchestrator with Flask/SocketIO for frontend communication."""

    def __init__(self, orchestrator: QuantumOrchestrator, config: Dict[str, Any]):
        """
        Initialize the server.

        Args:
            orchestrator (QuantumOrchestrator): The simulation orchestrator instance.
            config (Dict[str, Any]): Loaded configuration dictionary.
        """
        self.orchestrator = orchestrator
        self.config = config
        self.server_config = config.get("server", {})
        self.port = self.server_config.get("port", 8000) # Use API port from config

        # Ensure static/template folders exist relative to this script's location
        self.script_dir = Path(__file__).resolve().parent
        self.static_folder = self.script_dir / "static"
        self.template_folder = self.script_dir / "templates"
        # Create if they don't exist? Or assume setup script handles this?
        self.static_folder.mkdir(exist_ok=True)
        self.template_folder.mkdir(exist_ok=True)

        self.app = Flask(__name__,
                         static_folder=str(self.static_folder),
                         template_folder=str(self.template_folder))
        # Configure CORS (allow all for simplicity, restrict in production)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode="eventlet")

        self._register_routes()
        self._register_socketio_handlers()
        self.update_task = None

    def _register_routes(self):
        """Register basic HTTP routes."""
        @self.app.route('/')
        def index():
             # Serve a placeholder index.html if needed, or assume frontend handles routing
             index_path = self.template_folder / "index.html"
             if index_path.exists():
                  # Use Flask's send_from_directory for security
                  return send_from_directory(str(self.template_folder), 'index.html')
             else:
                  return "<h1>Quantum Kaleidoscope Hub</h1><p>Connect via Socket.IO</p>"

        # Add API endpoint for visualization data (polled by simple visualizer)
        @self.app.route('/api/visualization')
        def get_visualization_data():
             try:
                  # Use the orchestrator to get formatted data
                  state_data = self.orchestrator.get_current_state()
                  return jsonify(state_data)
             except Exception as e:
                  logger.error(f"Error getting visualization data: {e}", exc_info=True)
                  return jsonify({"error": "Failed to retrieve state"}), 500


    def _register_socketio_handlers(self):
        """Register Socket.IO event handlers."""
        @self.socketio.on('connect')
        def handle_connect():
            logger.info(f"Client connected: {request.sid}")
            try:
                # Send initial state upon connection
                emit('state_update', self.orchestrator.get_current_state())
            except Exception as e:
                 logger.error(f"Error sending initial state to {request.sid}: {e}", exc_info=True)

        @self.socketio.on('disconnect')
        def handle_disconnect():
            logger.info(f"Client disconnected: {request.sid}")

        @self.socketio.on('process_text')
        def handle_process_text(data):
             if not isinstance(data, dict):
                  emit('error', {'message': 'Invalid input format, expected JSON object'})
                  return
             text = data.get('text')
             if isinstance(text, str) and text:
                  logger.info(f"Received 'process_text' from {request.sid}")
                  # Process in background to avoid blocking socket
                  def background_task():
                       result = self.orchestrator.process_text(text)
                       if result:
                           # Emit result back to the specific client
                           emit('process_result', result, room=request.sid)
                       else:
                           emit('error', {'message': 'Text processing failed'}, room=request.sid)
                  self.socketio.start_background_task(background_task)
             else:
                  emit('error', {'message': 'Missing or invalid "text" field'}, room=request.sid)


        @self.socketio.on('get_state')
        def handle_get_state():
             logger.debug(f"Received 'get_state' from {request.sid}")
             try:
                 emit('state_update', self.orchestrator.get_current_state())
             except Exception as e:
                  logger.error(f"Error sending state to {request.sid}: {e}", exc_info=True)


    def _broadcast_updates(self):
        """Background task to periodically broadcast state updates."""
        logger.info("Starting state broadcast loop.")
        while self.orchestrator.running: # Use orchestrator running flag
            try:
                state = self.orchestrator.get_current_state()
                self.socketio.emit('state_update', state)
                logger.debug(f"Broadcasted state update. Nodes: {len(state['nodes'])}, Conns: {len(state['connections'])}")
            except Exception as e:
                 logger.error(f"Error during state broadcast: {e}", exc_info=True)
            # Use eventlet's sleep
            self.socketio.sleep(1.0) # Broadcast every second
        logger.info("State broadcast loop stopped.")


    def run(self):
        """Start the Flask-SocketIO server."""
        if self.orchestrator is None or not self.orchestrator.supernode:
             logger.critical("Cannot start server: Orchestrator or SuperNodeCore failed to initialize.")
             return

        logger.info(f"Starting Quantum Hub server on http://{self.config.get('host','0.0.0.0')}:{self.port}")
        # Start the periodic broadcast in a background greenlet
        self.update_task = self.socketio.start_background_task(self._broadcast_updates)
        try:
            # Use eventlet server
            self.socketio.run(self.app, host=self.config.get('host','0.0.0.0'), port=self.port, log_output=False)
        except OSError as e:
             logger.critical(f"Failed to start Hub server on port {self.port}: {e}. Is the port in use?", exc_info=True)
        except Exception as e:
            logger.critical(f"Quantum Hub server failed: {e}", exc_info=True)
        finally:
             logger.info("Quantum Hub server shutting down.")
             # Orchestrator should be stopped by main execution block or signal handler
             # if self.orchestrator.running:
             #      self.orchestrator.stop()


# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="Quantum Kaleidoscope Orchestration Hub")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to the main config.json file")
    # Allow overriding port via command line
    parser.add_argument("--port", type=int, help="Port to run the Hub server on (overrides config)")
    parser.add_argument("--log", help="Logging level (overrides config)")
    args = parser.parse_args()

    # Load configuration
    config = load_configuration(Path(args.config))

    # Setup logging level based on final config/args
    log_level_final = args.log or config.get("logging", {}).get("level", "INFO")
    log_level_to_set = getattr(logging, log_level_final.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level_to_set) # Root logger
    logger.setLevel(log_level_to_set) # This module's logger
    logger.info(f"Log level set to {log_level_final.upper()}")

    # Determine port
    hub_port = args.port or config.get("server", {}).get("port", 8000) # Use API port as Hub port? Or a separate one? Using API port for now.

    orchestrator = None
    server = None
    try:
        orchestrator = QuantumOrchestrator(config)
        orchestrator.start() # Start simulation loop
        server = QuantumKaleidoscopeServer(orchestrator, config)
        server.port = hub_port # Ensure server uses the determined port

        # Setup signal handlers for graceful shutdown
        def shutdown_handler(sig, frame):
             logger.info(f"Received signal {sig}, initiating shutdown...")
             if orchestrator: orchestrator.stop()
             # SocketIO server shutdown might need more specific handling depending on deployment
             # For eventlet, stopping the orchestrator loop might be enough if server runs in main thread
             # Or call sys.exit(0) ?
             raise KeyboardInterrupt # Use KeyboardInterrupt to break out of run

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        # Run the server
        server.run()

    except KeyboardInterrupt:
        logger.info("Hub stopped by user.")
    except Exception as e:
        logger.critical(f"Quantum Hub failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Finalizing shutdown...")
        if orchestrator and orchestrator.running:
             orchestrator.stop()
        logger.info("Exiting Quantum Hub.")


if __name__ == '__main__':
    main()
