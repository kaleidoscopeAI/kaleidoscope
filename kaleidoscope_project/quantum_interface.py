#!/usr/bin/env python3
"""
Quantum Interface for Kaleidoscope AI
=====================================
Provides a unified interface for quantum-inspired neural networks that integrate
with language models for enhanced pattern recognition and knowledge representation.

Features:
- Quantum-inspired network topology for representing knowledge
- Vector embeddings with quantum properties (superposition, entanglement)
- Synchronization between distributed nodes in a knowledge network
- Visualization of quantum state and connections
- Seamless integration with the unified LLM module
"""

import os
import sys
import time
import json
import uuid
import logging
import threading
import asyncio
import websockets
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("kaleidoscope_quantum.log")
    ]
)

logger = logging.getLogger("quantumInterface")

# Import unified_llm module if available
try:
    from unified_llm import UnifiedLLM, ModelProvider, ModelConfig, UnifiedLLMConfig, Message
    HAS_UNIFIED_LLM = True
except ImportError:
    logger.warning("unified_llm module not available. Some features will be limited.")
    HAS_UNIFIED_LLM = False

# Try to import optional dependencies
try:
    import scipy
    from scipy.sparse import csr_matrix
    from scipy.sparse.linalg import expm_multiply
    HAS_SCIPY = True
except ImportError:
    logger.warning("SciPy not available. Some quantum operations will be limited.")
    HAS_SCIPY = False

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    logger.warning("NetworkX not available. Graph operations will be limited.")
    HAS_NETWORKX = False

# ===== Constants =====
DEFAULT_DIMENSION = 128
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/kaleidoscope/quantum_config.json")
DEFAULT_DATA_DIR = os.path.expanduser("~/.local/share/kaleidoscope/quantum_data")

# ===== Core Classes =====

class NodeType(Enum):
    """Types of nodes in the quantum network"""
    CORE = auto()  # Central coordinator
    SEMANTIC = auto()  # Represents semantic concepts
    ENTITY = auto()  # Represents entities/objects
    RELATIONAL = auto()  # Represents relationships
    TEMPORAL = auto()  # Represents time-based patterns
    COMPUTATIONAL = auto()  # Represents computational resources

class ConnectionType(Enum):
    """Types of connections between nodes"""
    SEMANTIC = auto()  # Semantic relationship
    CAUSAL = auto()  # Causal relationship
    TEMPORAL = auto()  # Temporal relationship
    ENTANGLED = auto()  # Quantum entanglement

@dataclass
class QuantumState:
    """Represents a quantum state vector with phase and amplitude"""
    
    dimension: int = DEFAULT_DIMENSION
    state: Optional[np.ndarray] = None
    phase: float = 0.0
    energy: float = 1.0
    fidelity: float = 1.0
    stability: float = 1.0
    creation_time: float = field(default_factory=time.time)
    entangled_with: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Initialize state if not provided"""
        if self.state is None:
            self.state = self._init_state()
    
    def _init_state(self) -> np.ndarray:
        """Initialize a random quantum state"""
        # Use numpy random state with time-based seed
        rng = np.random.default_rng(int(time.time() * 1000) % (2**32))
        
        # Generate random complex state vector
        real_part = rng.normal(0, 1, self.dimension)
        imag_part = rng.normal(0, 1, self.dimension)
        state = real_part + 1j * imag_part
        
        # Normalize
        norm = np.linalg.norm(state)
        if norm > 1e-10:
            state = state / norm
        else:
            # Try again if we got an essentially zero vector (very unlikely)
            return self._init_state()
        
        return state
    
    def evolve(self, hamiltonian: np.ndarray, dt: float) -> None:
        """Evolve the quantum state according to the Schrödinger equation"""
        if not HAS_SCIPY:
            # Fallback for when scipy is not available
            # Simple approximation using matrix exponential
            evolution_matrix = np.eye(self.dimension) - 1j * hamiltonian * dt
            self.state = evolution_matrix @ self.state
            
            # Renormalize
            norm = np.linalg.norm(self.state)
            if norm > 1e-10:
                self.state = self.state / norm
            else:
                logger.warning("State collapsed to near-zero norm, reinitializing")
                self.state = self._init_state()
                self.fidelity = 0.0
            
            return
        
        try:
            # Use more accurate sparse matrix exponential method
            if not isinstance(hamiltonian, csr_matrix):
                hamiltonian_sparse = csr_matrix(hamiltonian)
            else:
                hamiltonian_sparse = hamiltonian
            
            # Apply evolution operator e^(-i*H*dt)
            self.state = expm_multiply(-1j * hamiltonian_sparse * dt, self.state)
            
            # Renormalize
            norm = np.linalg.norm(self.state)
            if norm > 1e-10:
                self.state = self.state / norm
            else:
                logger.warning("State collapsed to near-zero norm, reinitializing")
                self.state = self._init_state()
                self.fidelity = 0.0
        except Exception as e:
            logger.error(f"Error in quantum evolution: {e}")
            # Apply simple decoherence
            self.apply_decoherence(dt)
    
    def apply_decoherence(self, dt: float, rate: float = 0.05) -> None:
        """Apply decoherence (noise) to the quantum state"""
        # Simple model: mix with random state based on decoherence rate
        decoherence = np.exp(-rate * dt)
        
        if decoherence < 1.0:
            # Generate random state to mix with
            rng = np.random.default_rng()
            noise_real = rng.normal(0, 1, self.dimension)
            noise_imag = rng.normal(0, 1, self.dimension)
            noise = noise_real + 1j * noise_imag
            noise = noise / np.linalg.norm(noise)
            
            # Mix states
            mix_factor = np.sqrt(1.0 - decoherence**2)
            self.state = decoherence * self.state + mix_factor * noise
            
            # Renormalize
            norm = np.linalg.norm(self.state)
            if norm > 1e-10:
                self.state = self.state / norm
            
            # Update fidelity
            self.fidelity *= decoherence
    
    def measure(self, observable: np.ndarray) -> float:
        """Measure the quantum state using an observable operator"""
        try:
            # Calculate expectation value <ψ|O|ψ>
            if observable.shape != (self.dimension, self.dimension):
                raise ValueError(f"Observable shape {observable.shape} doesn't match state dimension {self.dimension}")
            
            # Apply observable and calculate inner product
            op_applied = observable @ self.state
            expectation = np.vdot(self.state, op_applied)
            
            # Return real part (expectation values of observables are real)
            return float(np.real(expectation))
        except Exception as e:
            logger.error(f"Error in quantum measurement: {e}")
            return 0.0
    
    def entangle_with(self, other_id: str) -> None:
        """Mark this state as entangled with another node"""
        self.entangled_with.add(other_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "dimension": self.dimension,
            "state_real": self.state.real.tolist(),
            "state_imag": self.state.imag.tolist(),
            "phase": self.phase,
            "energy": self.energy,
            "fidelity": self.fidelity,
            "stability": self.stability,
            "creation_time": self.creation_time,
            "entangled_with": list(self.entangled_with)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuantumState':
        """Create a QuantumState from a dictionary"""
        try:
            dimension = data.get("dimension", DEFAULT_DIMENSION)
            state_real = np.array(data.get("state_real", []))
            state_imag = np.array(data.get("state_imag", []))
            
            if len(state_real) == 0 or len(state_imag) == 0:
                # No valid state data, create new state
                state = None
            else:
                # Reconstruct complex state vector
                state = state_real + 1j * state_imag
            
            return cls(
                dimension=dimension,
                state=state,
                phase=data.get("phase", 0.0),
                energy=data.get("energy", 1.0),
                fidelity=data.get("fidelity", 1.0),
                stability=data.get("stability", 1.0),
                creation_time=data.get("creation_time", time.time()),
                entangled_with=set(data.get("entangled_with", []))
            )
        except Exception as e:
            logger.error(f"Error deserializing quantum state: {e}")
            return cls(dimension=dimension)

@dataclass
class QuantumNode:
    """A node in the quantum network"""
    
    id: str
    name: str
    type: NodeType = NodeType.SEMANTIC
    state: QuantumState = field(default_factory=QuantumState)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    connections: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.name,
            "state": self.state.to_dict(),
            "position": list(self.position),
            "connections": self.connections,
            "metadata": self.metadata,
            "creation_time": self.creation_time,
            "last_update": self.last_update
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuantumNode':
        """Create a QuantumNode from a dictionary"""
        try:
            node_type = NodeType[data.get("type", "SEMANTIC")]
            state_data = data.get("state", {})
            state = QuantumState.from_dict(state_data)
            
            position = tuple(data.get("position", [0.0, 0.0, 0.0]))
            if len(position) != 3:
                position = (0.0, 0.0, 0.0)
            
            return cls(
                id=data.get("id", str(uuid.uuid4())),
                name=data.get("name", "Unnamed Node"),
                type=node_type,
                state=state,
                position=position,
                connections=data.get("connections", {}),
                metadata=data.get("metadata", {}),
                creation_time=data.get("creation_time", time.time()),
                last_update=data.get("last_update", time.time())
            )
        except Exception as e:
            logger.error(f"Error deserializing quantum node: {e}")
            node_id = data.get("id", str(uuid.uuid4()))
            return cls(id=node_id, name=f"Error Node {node_id[:8]}")

@dataclass
class QuantumConnection:
    """A connection between two quantum nodes"""
    
    source_id: str
    target_id: str
    strength: float = 0.5
    type: ConnectionType = ConnectionType.SEMANTIC
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "strength": self.strength,
            "type": self.type.name,
            "metadata": self.metadata,
            "creation_time": self.creation_time,
            "last_update": self.last_update
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuantumConnection':
        """Create a QuantumConnection from a dictionary"""
        try:
            conn_type = ConnectionType[data.get("type", "SEMANTIC")]
            
            return cls(
                source_id=data.get("source_id", ""),
                target_id=data.get("target_id", ""),
                strength=data.get("strength", 0.5),
                type=conn_type,
                metadata=data.get("metadata", {}),
                creation_time=data.get("creation_time", time.time()),
                last_update=data.get("last_update", time.time())
            )
        except Exception as e:
            logger.error(f"Error deserializing quantum connection: {e}")
            return cls(
                source_id=data.get("source_id", ""),
                target_id=data.get("target_id", "")
            )

@dataclass
class QuantumNetworkEvent:
    """An event in the quantum network"""
    
    type: str
    message: str
    timestamp: float = field(default_factory=time.time)
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "type": self.type,
            "message": self.message,
            "timestamp": self.timestamp,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "metadata": self.metadata
        }

@dataclass
class QuantumNetworkState:
    """The state of the entire quantum network"""
    
    nodes: Dict[str, QuantumNode] = field(default_factory=dict)
    connections: List[QuantumConnection] = field(default_factory=list)
    events: List[QuantumNetworkEvent] = field(default_factory=list)
    global_state: QuantumState = field(default_factory=QuantumState)
    metrics: Dict[str, Any] = field(default_factory=dict)
    last_update: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "connections": [conn.to_dict() for conn in self.connections],
            "events": [event.to_dict() for event in self.events[-100:]],  # Limit to last 100 events
            "global_state": self.global_state.to_dict(),
            "metrics": self.metrics,
            "last_update": self.last_update
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuantumNetworkState':
        """Create a QuantumNetworkState from a dictionary"""
        try:
            # Load nodes
            nodes = {}
            for node_id, node_data in data.get("nodes", {}).items():
                nodes[node_id] = QuantumNode.from_dict(node_data)
            
            # Load connections
            connections = []
            for conn_data in data.get("connections", []):
                connections.append(QuantumConnection.from_dict(conn_data))
            
            # Load events
            events = []
            for event_data in data.get("events", []):
                event = QuantumNetworkEvent(
                    type=event_data.get("type", "unknown"),
                    message=event_data.get("message", ""),
                    timestamp=event_data.get("timestamp", time.time()),
                    source_id=event_data.get("source_id"),
                    target_id=event_data.get("target_id"),
                    metadata=event_data.get("metadata", {})
                )
                events.append(event)
            
            # Load global state
            global_state_data = data.get("global_state", {})
            global_state = QuantumState.from_dict(global_state_data)
            
            return cls(
                nodes=nodes,
                connections=connections,
                events=events,
                global_state=global_state,
                metrics=data.get("metrics", {}),
                last_update=data.get("last_update", time.time())
            )
        except Exception as e:
            logger.error(f"Error deserializing quantum network state: {e}")
            return cls()

@dataclass
class QuantumConfig:
    """Configuration for the quantum network"""
    
    dimension: int = DEFAULT_DIMENSION
    simulation_interval: float = 0.1
    decoherence_rate: float = 0.01
    entanglement_threshold: float = 0.7
    max_nodes: int = 1000
    server_url: str = "ws://localhost:8765"
    data_dir: str = DEFAULT_DATA_DIR
    auto_save: bool = True
    save_interval: float = 60.0
    log_level: str = "INFO"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "dimension": self.dimension,
            "simulation_interval": self.simulation_interval,
            "decoherence_rate": self.decoherence_rate,
            "entanglement_threshold": self.entanglement_threshold,
            "max_nodes": self.max_nodes,
            "server_url": self.server_url,
            "data_dir": self.data_dir,
            "auto_save": self.auto_save,
            "save_interval": self.save_interval,
            "log_level": self.log_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuantumConfig':
        """Create a QuantumConfig from a dictionary"""
        return cls(
            dimension=data.get("dimension", DEFAULT_DIMENSION),
            simulation_interval=data.get("simulation_interval", 0.1),
            decoherence_rate=data.get("decoherence_rate", 0.01),
            entanglement_threshold=data.get("entanglement_threshold", 0.7),
            max_nodes=data.get("max_nodes", 1000),
            server_url=data.get("server_url", "ws://localhost:8765"),
            data_dir=data.get("data_dir", DEFAULT_DATA_DIR),
            auto_save=data.get("auto_save", True),
            save_interval=data.get("save_interval", 60.0),
            log_level=data.get("log_level", "INFO")
        )
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'QuantumConfig':
        """Load configuration from file"""
        config_path = config_path or DEFAULT_CONFIG_PATH
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return cls.from_dict(config_data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load config from {config_path}: {e}. Using defaults.")
            return cls()
    
    def save(self, config_path: Optional[str] = None) -> bool:
        """Save configuration to file"""
        config_path = config_path or DEFAULT_CONFIG_PATH
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")
            return False

# ===== Main Interface =====

class QuantumInterface:
    """Main interface for the quantum network"""
    
    def __init__(self, config: Optional[QuantumConfig] = None,
                 llm: Optional['UnifiedLLM'] = None):
        """Initialize the quantum interface"""
        self.config = config or QuantumConfig()
        self.state = QuantumNetworkState()
        self.state_lock = threading.RLock()
        self.running = threading.Event()
        self.llm = llm
        
        # Set up simulation thread
        self.simulation_thread = None
        
        # Set up WebSocket server
        self.server = None
        self.clients = set()
        
        # Set up observables
        self._setup_observables()
        
        # Create data directory
        os.makedirs(self.config.data_dir, exist_ok=True)
        
        # Create core node
        with self.state_lock:
            if len(self.state.nodes) == 0:
                self._create_core_node()
    
    def _create_core_node(self) -> str:
        """Create the core node of the network"""
        core_id = "core-" + str(uuid.uuid4())[:8]
        core_node = QuantumNode(
            id=core_id,
            name="Core Node",
            type=NodeType.CORE,
            state=QuantumState(dimension=self.config.dimension),
            position=(0.0, 0.0, 0.0)
        )
        self.state.nodes[core_id] = core_node
        
        # Create initial event
        self.state.events.append(QuantumNetworkEvent(
            type="initialization",
            message="Core node created",
            source_id=core_id
        ))
        
        return core_id
    
    def _setup_observables(self) -> None:
        """Set up quantum observables"""
        dim = self.config.dimension
        self.observables = {}
        
        # Create Hermitian operators for different observables
        try:
            rng = np.random.default_rng(12345)  # Fixed seed for reproducibility
            
            # Energy observable (diagonal with random energies)
            energy_diag = rng.uniform(0, 1, dim)
            energy_matrix = np.diag(energy_diag)
            self.observables["energy"] = energy_matrix
            
            # Position observable (tridiagonal matrix)
            pos_diag = np.zeros(dim)
            for i in range(dim):
                # Position increases linearly from -1 to 1
                pos_diag[i] = 2 * (i / (dim - 1)) - 1
            self.observables["position"] = np.diag(pos_diag)
            
            # Momentum observable (off-diagonal elements)
            momentum = np.zeros((dim, dim), dtype=complex)
            for i in range(dim-1):
                momentum[i, i+1] = 1j
                momentum[i+1, i] = -1j
            self.observables["momentum"] = momentum
            
            # Coherence observable (measure of phase coherence)
            coherence = np.zeros((dim, dim), dtype=complex)
            for i in range(dim):
                for j in range(dim):
                    phase = 2 * np.pi * (i - j) / dim
                    coherence[i, j] = np.exp(1j * phase)
            self.observables["coherence"] = coherence
            
            logger.info(f"Quantum observables initialized with dimension {dim}")
        
        except Exception as e:
            logger.error(f"Error setting up observables: {e}")
            # Create simple fallback observables
            self.observables = {
                "energy": np.eye(dim),
                "position": np.eye(dim),
                "momentum": np.eye(dim),
                "coherence": np.eye(dim)
            }
    
    def start(self) -> None:
        """Start the quantum interface"""
        if self.running.is_set():
            logger.warning("Quantum interface already running")
            return
        
        self.running.set()
        
        # Start simulation thread
        self.simulation_thread = threading.Thread(target=self._simulation_loop)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        
        # Start WebSocket server in a new thread
        server_thread = threading.Thread(target=self._start_server)
        server_thread.daemon = True
        server_thread.start()
        
        logger.info("Quantum interface started")
    
    def stop(self) -> None:
        """Stop the quantum interface"""
        if not self.running.is_set():
            logger.warning("Quantum interface not running")
            return
        
        logger.info("Stopping quantum interface")
        self.running.clear()
        
        # Stop WebSocket server
        if self.server:
            asyncio.run(self._stop_server())
        
        # Wait for simulation thread to finish
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=5.0)
        
        # Save state
        self.save_state()
        
        logger.info("Quantum interface stopped")
    
    def _simulation_loop(self) -> None:
        """Main simulation loop"""
        last_save_time = time.time()
        
        while self.running.is_set():
            start_time = time.time()
            
            try:
                with self.state_lock:
                    # Calculate global Hamiltonian
                    hamiltonian = self._calculate_global_hamiltonian()
                    
                    # Update all nodes
                    for node_id, node in self.state.nodes.items():
                        # Apply evolution
                        node.state.evolve(hamiltonian, self.config.simulation_interval)
                        
                        # Apply decoherence
                        node.state.apply_decoherence(
                            self.config.simulation_interval,
                            self.config.decoherence_rate
                        )
                        
                        # Update energy and stability
                        node.state.energy = max(0.1, node.state.measure(self.observables["energy"]))
                        coherence = node.state.measure(self.observables["coherence"])
                        node.state.stability = max(0.1, (coherence + 1) / 2)
                        
                        # Update timestamp
                        node.last_update = time.time()
                    
                    # Update global state
                    if len(self.state.nodes) > 0:
                        self._update_global_state()
                    
                    # Update metrics
                    self._update_metrics()
                    
                    # Update timestamp
                    self.state.last_update = time.time()
                
                # Broadcast state update to clients
                if self.clients:
                    asyncio.run(self._broadcast_state_update())
                
                # Auto-save if enabled
                current_time = time.time()
                if (self.config.auto_save and 
                    current_time - last_save_time > self.config.save_interval):
                    self.save_state()
                    last_save_time = current_time
            
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
            
            # Calculate sleep time
            elapsed = time.time() - start_time
            sleep_time = max(0.0, self.config.simulation_interval - elapsed)
            time.sleep(sleep_time)
    
    def _calculate_global_hamiltonian(self) -> np.ndarray:
        """Calculate the global Hamiltonian for the quantum network"""
        dim = self.config.dimension
        
        # Start with zero matrix
        hamiltonian = np.zeros((dim, dim), dtype=complex)
        
        # Add contribution from node connections
        for conn in self.state.connections:
            source_id = conn.source_id
            target_id = conn.target_id
            
            if source_id in self.state.nodes and target_id in self.state.nodes:
                source_node = self.state.nodes[source_id]
                target_node = self.state.nodes[target_id]
                
                # Create interaction term based on connection strength
                interaction = conn.strength * np.outer(
                    source_node.state.state.conj(),
                    target_node.state.state
                )
                
                hamiltonian += interaction + interaction.conj().T
        
        # Add energy terms from individual nodes
        for node_id, node in self.state.nodes.items():
            # Diagonal energy contribution
            energy_contrib = node.state.energy * np.diag(
                np.abs(node.state.state)**2
            )
            hamiltonian += energy_contrib
        
        # Ensure Hamiltonian is Hermitian (should be by construction, but ensure it)
        hamiltonian = 0.5 * (hamiltonian + hamiltonian.conj().T)
        
        return hamiltonian
    
    def _update_global_state(self) -> None:
        """Update the global quantum state"""
        # Simple approach: average of all node states weighted by energy
        global_state = np.zeros(self.config.dimension, dtype=complex)
        total_energy = 0.0
        
        for node_id, node in self.state.nodes.items():
            global_state += node.state.energy * node.state.state
            total_energy += node.state.energy
        
        if total_energy > 0:
            global_state /= total_energy
            
            # Normalize
            norm = np.linalg.norm(global_state)
            if norm > 1e-10:
                global_state /= norm
                
                # Update the global state
                self.state.global_state.state = global_state
                
                # Update global state energy and stability
                self.state.global_state.energy = np.mean([
                    node.state.energy for node in self.state.nodes.values()
                ])
                self.state.global_state.stability = np.mean([
                    node.state.stability for node in self.state.nodes.values()
                ])
                
                # Update phase
                self.state.global_state.phase += 0.1 * self.config.simulation_interval
                while self.state.global_state.phase > 2 * np.pi:
                    self.state.global_state.phase -= 2 * np.pi
    
    def _update_metrics(self) -> None:
        """Update network metrics"""
        self.state.metrics.update({
            "node_count": len(self.state.nodes),
            "connection_count": len(self.state.connections),
            "avg_energy": np.mean([node.state.energy for node in self.state.nodes.values()]) if self.state.nodes else 0,
            "avg_stability": np.mean([node.state.stability for node in self.state.nodes.values()]) if self.state.nodes else 0,
            "global_energy": self.state.global_state.energy,
            "global_stability": self.state.global_state.stability,
            "entangled_node_count": sum(1 for node in self.state.nodes.values() if node.state.entangled_with),
            "avg_connection_strength": np.mean([conn.strength for conn in self.state.connections]) if self.state.connections else 0,
            "simulation_time": time.time()
        })
    
    async def _start_server(self) -> None:
        """Start WebSocket server"""
        try:
            host = "0.0.0.0"
            port = int(self.config.server_url.split(":")[-1]) if ":" in self.config.server_url else 8765
            
            # Parse URL to get host and port
            if self.config.server_url.startswith("ws://"):
                url_parts = self.config.server_url[5:].split(":")
                if len(url_parts) > 1:
                    host = url_parts[0]
                    port = int(url_parts[1].split("/")[0])
            
            self.server = await websockets.serve(
                self._handle_client,
                host, port
            )
            
            logger.info(f"WebSocket server started on ws://{host}:{port}")
            
            # Keep server running
            await self.server.wait_closed()
            
        except Exception as e:
            logger.error(f"Error starting WebSocket server: {e}")
    
    async def _stop_server(self) -> None:
        """Stop WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")
    
    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str) -> None:
        """Handle WebSocket client"""
        # Add client to set
        self.clients.add(websocket)
        
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "welcome",
                "message": "Connected to Quantum Network Server",
                "node_count": len(self.state.nodes),
                "time": time.time()
            }))
            
            # Send initial state
            with self.state_lock:
                state_dict = self.state.to_dict()
            
            await websocket.send(json.dumps({
                "type": "state_update",
                "data": state_dict
            }))
            
            # Process messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_client_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
                except Exception as e:
                    logger.error(f"Error processing client message: {e}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": f"Server error: {str(e)}"
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Remove client from set
            self.clients.remove(websocket)
    
    async def _process_client_message(self, websocket: websockets.WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Process client message"""
        message_type = data.get("type", "")
        
        if message_type == "create_node":
            # Create a new node
            node_type_str = data.get("node_type", "SEMANTIC")
            try:
                node_type = NodeType[node_type_str]
            except KeyError:
                node_type = NodeType.SEMANTIC
            
            with self.state_lock:
                node_id = self.create_node(
                    name=data.get("name", "Client Node"),
                    node_type=node_type,
                    position=tuple(data.get("position", (0.0, 0.0, 0.0))),
                    metadata=data.get("metadata", {})
                )
            
            await websocket.send(json.dumps({
                "type": "node_created",
                "node_id": node_id
            }))
        
        elif message_type == "create_connection":
            # Create a connection between nodes
            source_id = data.get("source_id")
            target_id = data.get("target_id")
            
            if not source_id or not target_id:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Missing source_id or target_id"
                }))
                return
            
            conn_type_str = data.get("connection_type", "SEMANTIC")
            try:
                conn_type = ConnectionType[conn_type_str]
            except KeyError:
                conn_type = ConnectionType.SEMANTIC
            
            with self.state_lock:
                success = self.create_connection(
                    source_id=source_id,
                    target_id=target_id,
                    strength=data.get("strength", 0.5),
                    conn_type=conn_type,
                    metadata=data.get("metadata", {})
                )
            
            if success:
                await websocket.send(json.dumps({
                    "type": "connection_created",
                    "source_id": source_id,
                    "target_id": target_id
                }))
            else:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Failed to create connection"
                }))
        
        elif message_type == "delete_node":
            # Delete a node
            node_id = data.get("node_id")
            
            if not node_id:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Missing node_id"
                }))
                return
            
            with self.state_lock:
                success = self.delete_node(node_id)
            
            if success:
                await websocket.send(json.dumps({
                    "type": "node_deleted",
                    "node_id": node_id
                }))
            else:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Failed to delete node"
                }))
        
        elif message_type == "process_text":
            # Process text with LLM
            text = data.get("text", "")
            
            if not text:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Missing or empty text"
                }))
                return
            
            # Process text with LLM
            result = await self._process_text_with_llm(text)
            
            await websocket.send(json.dumps({
                "type": "text_processed",
                "original_text": text,
                "result": result
            }))
        
        elif message_type == "get_state":
            # Send current state
            with self.state_lock:
                state_dict = self.state.to_dict()
            
            await websocket.send(json.dumps({
                "type": "state_update",
                "data": state_dict
            }))
        
        elif message_type == "ping":
            # Simple ping-pong
            await websocket.send(json.dumps({
                "type": "pong",
                "time": time.time()
            }))
    
    async def _broadcast_state_update(self) -> None:
        """Broadcast state update to all clients"""
        if not self.clients:
            return
        
        try:
            with self.state_lock:
                state_dict = self.state.to_dict()
            
            message = json.dumps({
                "type": "state_update",
                "data": state_dict
            })
            
            # Broadcast to all connected clients
            disconnected_clients = set()
            for client in self.clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)
                except Exception as e:
                    logger.error(f"Error sending message to client: {e}")
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.clients.remove(client)
        
        except Exception as e:
            logger.error(f"Error broadcasting state update: {e}")
    
    async def _process_text_with_llm(self, text: str) -> Dict[str, Any]:
        """Process text with LLM and integrate into quantum network"""
        if not self.llm and not HAS_UNIFIED_LLM:
            return {
                "error": "LLM module not available",
                "node_id": None
            }
        
        try:
            # Create a vector representation using LLM
            if self.llm:
                # Use the provided LLM
                system_prompt = """
                Analyze the following text and create a conceptual representation.
                Identify key concepts, relationships, and semantic features.
                Return your analysis as JSON with the following structure:
                {
                    "concepts": ["concept1", "concept2", ...],
                    "relationships": [{"source": "concept1", "target": "concept2", "type": "relation_type"}],
                    "features": [0.1, 0.2, ...],
                    "summary": "Brief summary"
                }
                """
                
                messages = [
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=text)
                ]
                
                result = self.llm.chat_complete(messages)
                
                try:
                    analysis = json.loads(result.text)
                except json.JSONDecodeError:
                    # Extract JSON from text if not properly formatted
                    import re
                    json_match = re.search(r'```json\n(.*?)\n```', result.text, re.DOTALL)
                    if json_match:
                        try:
                            analysis = json.loads(json_match.group(1))
                        except json.JSONDecodeError:
                            analysis = {
                                "concepts": [],
                                "relationships": [],
                                "features": [],
                                "summary": "Error parsing LLM output"
                            }
                    else:
                        analysis = {
                            "concepts": [],
                            "relationships": [],
                            "features": [],
                            "summary": "Error parsing LLM output"
                        }
            else:
                # Create simple representation without LLM
                import hashlib
                hash_obj = hashlib.md5(text.encode())
                hash_bytes = hash_obj.digest()
                
                # Create features from hash
                features = []
                for i in range(min(self.config.dimension, 16)):
                    # Convert hash bytes to values between -1 and 1
                    val = ((hash_bytes[i % 16] / 255) * 2) - 1
                    features.append(val)
                
                # Pad to dimension
                features.extend([0.0] * (self.config.dimension - len(features)))
                
                # Simple analysis
                words = text.split()
                concepts = []
                for i in range(min(5, len(words))):
                    if len(words[i]) > 3:  # Only use words longer than 3 chars
                        concepts.append(words[i])
                
                analysis = {
                    "concepts": concepts,
                    "relationships": [],
                    "features": features,
                    "summary": f"Text with {len(words)} words"
                }
            
            # Create quantum state from features
            features = analysis.get("features", [])
            if len(features) < self.config.dimension:
                # Pad with zeros
                features.extend([0.0] * (self.config.dimension - len(features)))
            elif len(features) > self.config.dimension:
                # Truncate
                features = features[:self.config.dimension]
            
            # Normalize features to create state vector
            features_array = np.array(features, dtype=complex)
            norm = np.linalg.norm(features_array)
            if norm > 1e-10:
                state_vector = features_array / norm
            else:
                # Use random state if features are essentially zero
                state = QuantumState(dimension=self.config.dimension)
                state_vector = state.state
            
            # Create a semantic node
            with self.state_lock:
                node_id = self.create_node(
                    name=analysis.get("summary", "Text Node"),
                    node_type=NodeType.SEMANTIC,
                    metadata={
                        "text_sample": text[:100] + ("..." if len(text) > 100 else ""),
                        "concepts": analysis.get("concepts", []),
                        "source": "text_processing"
                    }
                )
                
                # Set state vector
                if node_id in self.state.nodes:
                    self.state.nodes[node_id].state.state = state_vector
                
                # Create connections based on relationships
                for rel in analysis.get("relationships", []):
                    # Try to find or create concept nodes
                    source_concept = rel.get("source")
                    target_concept = rel.get("target")
                    
                    if source_concept and target_concept:
                        # Create concept nodes if they don't exist
                        source_id = self._find_or_create_concept_node(source_concept)
                        target_id = self._find_or_create_concept_node(target_concept)
                        
                        # Create connections
                        if source_id and target_id:
                            self.create_connection(
                                source_id=source_id,
                                target_id=target_id,
                                strength=0.7,
                                conn_type=ConnectionType.SEMANTIC,
                                metadata={"relation_type": rel.get("type", "semantic")}
                            )
                
                # Connect to similar nodes
                self._connect_to_similar_nodes(node_id)
            
            return {
                "node_id": node_id,
                "concepts": analysis.get("concepts", []),
                "summary": analysis.get("summary", ""),
                "connections": [c.to_dict() for c in self.state.connections if c.source_id == node_id or c.target_id == node_id]
            }
        
        except Exception as e:
            logger.error(f"Error processing text with LLM: {e}")
            return {
                "error": str(e),
                "node_id": None
            }
    
    def _find_or_create_concept_node(self, concept: str) -> Optional[str]:
        """Find or create a node for a concept"""
        # Check if a node for this concept already exists
        for node_id, node in self.state.nodes.items():
            if "concept" in node.metadata and node.metadata["concept"] == concept:
                return node_id
        
        # Create new concept node
        return self.create_node(
            name=concept,
            node_type=NodeType.ENTITY,
            metadata={"concept": concept, "source": "concept_extraction"}
        )
    
    def _connect_to_similar_nodes(self, node_id: str, max_connections: int = 3) -> None:
        """Connect a node to similar nodes"""
        if node_id not in self.state.nodes:
            return
        
        node = self.state.nodes[node_id]
        
        # Calculate similarity with all other nodes
        similarities = []
        for other_id, other_node in self.state.nodes.items():
            if other_id != node_id:
                # Calculate vector similarity
                similarity = self._calculate_state_similarity(
                    node.state.state, other_node.state.state
                )
                
                similarities.append((other_id, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Create connections for top matches
        for other_id, similarity in similarities[:max_connections]:
            if similarity > self.config.entanglement_threshold:
                self.create_connection(
                    source_id=node_id,
                    target_id=other_id,
                    strength=similarity,
                    conn_type=ConnectionType.SEMANTIC,
                    metadata={"similarity": similarity}
                )
                
                # Create entanglement for higher similarities
                if similarity > 0.9:
                    node.state.entangle_with(other_id)
                    self.state.nodes[other_id].state.entangle_with(node_id)
    
    def _calculate_state_similarity(self, state1: np.ndarray, state2: np.ndarray) -> float:
        """Calculate similarity between two quantum states"""
        # Calculate fidelity (squared inner product)
        fidelity = np.abs(np.vdot(state1, state2))**2
        return float(fidelity)
    
    def create_node(self, name: str, node_type: NodeType = NodeType.SEMANTIC,
                   position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                   metadata: Dict[str, Any] = None) -> str:
        """Create a new node in the network"""
        # Check max nodes limit
        if len(self.state.nodes) >= self.config.max_nodes:
            logger.warning(f"Max nodes limit ({self.config.max_nodes}) reached")
            return ""
        
        # Generate ID
        node_id = f"{node_type.name.lower()}-{str(uuid.uuid4())[:8]}"
        
        # Create node
        node = QuantumNode(
            id=node_id,
            name=name,
            type=node_type,
            state=QuantumState(dimension=self.config.dimension),
            position=position,
            metadata=metadata or {}
        )
        
        # Add to network
        self.state.nodes[node_id] = node
        
        # Add event
        self.state.events.append(QuantumNetworkEvent(
            type="node_created",
            message=f"Node created: {name}",
            source_id=node_id,
            metadata={"node_type": node_type.name}
        ))
        
        logger.debug(f"Created node: {name} ({node_id})")
        
        return node_id
    
    def delete_node(self, node_id: str) -> bool:
        """Delete a node from the network"""
        if node_id not in self.state.nodes:
            return False
        
        # Get node
        node = self.state.nodes[node_id]
        
        # Remove from network
        del self.state.nodes[node_id]
        
        # Remove connected connections
        self.state.connections = [
            conn for conn in self.state.connections
            if conn.source_id != node_id and conn.target_id != node_id
        ]
        
        # Remove entanglement references
        for other_id, other_node in self.state.nodes.items():
            if node_id in other_node.state.entangled_with:
                other_node.state.entangled_with.remove(node_id)
        
        # Add event
        self.state.events.append(QuantumNetworkEvent(
            type="node_deleted",
            message=f"Node deleted: {node.name}",
            source_id=node_id,
            metadata={"node_type": node.type.name}
        ))
        
        logger.debug(f"Deleted node: {node.name} ({node_id})")
        
        return True
    
    def create_connection(self, source_id: str, target_id: str, strength: float = 0.5,
                         conn_type: ConnectionType = ConnectionType.SEMANTIC,
                         metadata: Dict[str, Any] = None) -> bool:
        """Create a connection between two nodes"""
        # Validate node IDs
        if source_id not in self.state.nodes or target_id not in self.state.nodes:
            logger.warning(f"Cannot create connection: node not found")
            return False
        
        # Check for existing connection
        for conn in self.state.connections:
            if ((conn.source_id == source_id and conn.target_id == target_id) or
                (conn.source_id == target_id and conn.target_id == source_id)):
                # Update existing connection
                conn.strength = strength
                conn.type = conn_type
                if metadata:
                    conn.metadata.update(metadata)
                conn.last_update = time.time()
                return True
        
        # Create new connection
        connection = QuantumConnection(
            source_id=source_id,
            target_id=target_id,
            strength=strength,
            type=conn_type,
            metadata=metadata or {}
        )
        
        # Add to network
        self.state.connections.append(connection)
        
        # Add event
        self.state.events.append(QuantumNetworkEvent(
            type="connection_created",
            message=f"Connection created",
            source_id=source_id,
            target_id=target_id,
            metadata={"connection_type": conn_type.name, "strength": strength}
        ))
        
        # Create entanglement for strong connections
        if strength > self.config.entanglement_threshold:
            self.state.nodes[source_id].state.entangle_with(target_id)
            self.state.nodes[target_id].state.entangle_with(source_id)
        
        logger.debug(f"Created connection: {source_id} -> {target_id} (strength: {strength})")
        
        return True
    
    def delete_connection(self, source_id: str, target_id: str) -> bool:
        """Delete a connection between two nodes"""
        # Find connection
        for i, conn in enumerate(self.state.connections):
            if ((conn.source_id == source_id and conn.target_id == target_id) or
                (conn.source_id == target_id and conn.target_id == source_id)):
                # Remove connection
                self.state.connections.pop(i)
                
                # Remove entanglement if it exists
                if source_id in self.state.nodes and target_id in self.state.nodes:
                    if target_id in self.state.nodes[source_id].state.entangled_with:
                        self.state.nodes[source_id].state.entangled_with.remove(target_id)
                    if source_id in self.state.nodes[target_id].state.entangled_with:
                        self.state.nodes[target_id].state.entangled_with.remove(source_id)
                
                # Add event
                self.state.events.append(QuantumNetworkEvent(
                    type="connection_deleted",
                    message=f"Connection deleted",
                    source_id=source_id,
                    target_id=target_id
                ))
                
                logger.debug(f"Deleted connection: {source_id} -> {target_id}")
                
                return True
        
        return False
    
    def save_state(self, file_path: Optional[str] = None) -> bool:
        """Save network state to file"""
        if not file_path:
            # Use default path
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.config.data_dir, f"quantum_state_{timestamp}.json")
        
        try:
            with self.state_lock:
                state_dict = self.state.to_dict()
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(state_dict, f, indent=2)
            
            logger.info(f"Saved network state to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving network state: {e}")
            return False
    
    def load_state(self, file_path: str) -> bool:
        """Load network state from file"""
        try:
            with open(file_path, 'r') as f:
                state_dict = json.load(f)
            
            with self.state_lock:
                self.state = QuantumNetworkState.from_dict(state_dict)
            
            logger.info(f"Loaded network state from {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error loading network state: {e}")
            return False
    
    def process_text(self, text: str) -> Dict[str, Any]:
        """Process text and integrate into quantum network"""
        # Run in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._process_text_with_llm(text))
    
    def measure_network_properties(self) -> Dict[str, float]:
        """Measure global properties of the quantum network"""
        if not HAS_NETWORKX:
            return {}
        
        with self.state_lock:
            if len(self.state.nodes) == 0:
                return {}
            
            try:
                # Create NetworkX graph from current state
                G = nx.Graph()
                
                # Add nodes
                for node_id, node in self.state.nodes.items():
                    G.add_node(node_id, name=node.name, type=node.type.name)
                
                # Add edges
                for conn in self.state.connections:
                    G.add_edge(conn.source_id, conn.target_id, weight=conn.strength)
                
                # Calculate metrics
                metrics = {}
                
                # Basic metrics
                metrics["node_count"] = len(G)
                metrics["edge_count"] = G.number_of_edges()
                
                if len(G) > 1:
                    # Connected components
                    components = list(nx.connected_components(G))
                    metrics["component_count"] = len(components)
                    
                    # Largest component
                    largest_component = max(components, key=len)
                    metrics["largest_component_size"] = len(largest_component)
                    
                    # Create subgraph for largest component
                    largest_G = G.subgraph(largest_component).copy()
                    
                    if len(largest_G) > 1:
                        # Average path length (only in largest component)
                        try:
                            metrics["avg_path_length"] = nx.average_shortest_path_length(largest_G)
                        except nx.NetworkXError:
                            metrics["avg_path_length"] = float('inf')
                        
                        # Clustering coefficient
                        metrics["clustering_coefficient"] = nx.average_clustering(largest_G)
                        
                        # Diameter
                        try:
                            metrics["diameter"] = nx.diameter(largest_G)
                        except nx.NetworkXError:
                            metrics["diameter"] = float('inf')
                
                # Density
                metrics["density"] = nx.density(G)
                
                # Centrality measures (use largest component to avoid infinite values)
                if len(G) > 1 and 'largest_G' in locals():
                    # Degree centrality
                    degree_centrality = nx.degree_centrality(largest_G)
                    metrics["avg_degree_centrality"] = sum(degree_centrality.values()) / len(degree_centrality)
                    metrics["max_degree_centrality"] = max(degree_centrality.values())
                    
                    # Betweenness centrality
                    betweenness_centrality = nx.betweenness_centrality(largest_G)
                    metrics["avg_betweenness_centrality"] = sum(betweenness_centrality.values()) / len(betweenness_centrality)
                    metrics["max_betweenness_centrality"] = max(betweenness_centrality.values())
                
                return metrics
            
            except Exception as e:
                logger.error(f"Error measuring network properties: {e}")
                return {}

# ===== Command Line Interface =====

def create_cli_parser():
    """Create command line argument parser"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Quantum Interface for Kaleidoscope AI")
    
    # Configuration
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--dimension", type=int, help="Dimension of quantum state space")
    parser.add_argument("--server-url", help="WebSocket server URL")
    parser.add_argument("--data-dir", help="Data directory")
    
    # Commands
    parser.add_argument("--start", action="store_true", help="Start quantum interface")
    parser.add_argument("--stop", action="store_true", help="Stop quantum interface")
    parser.add_argument("--save", help="Save network state to file")
    parser.add_argument("--load", help="Load network state from file")
    
    # Text processing
    parser.add_argument("--process-text", help="Process text and integrate into network")
    parser.add_argument("--process-file", help="Process text file and integrate into network")
    
    # Network manipulation
    parser.add_argument("--create-node", help="Create a new node with the given name")
    parser.add_argument("--node-type", choices=[t.name for t in NodeType], 
                        help="Type of node to create")
    parser.add_argument("--create-connection", nargs=2, metavar=("SOURCE_ID", "TARGET_ID"),
                        help="Create a connection between two nodes")
    parser.add_argument("--connection-strength", type=float, default=0.5,
                        help="Strength of connection")
    
    # Utility
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    return parser

def main():
    """Main entry point"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Load configuration
    config = QuantumConfig.load(args.config)
    
    # Override with command line arguments
    if args.dimension:
        config.dimension = args.dimension
    if args.server_url:
        config.server_url = args.server_url
    if args.data_dir:
        config.data_dir = args.data_dir
    
    # Create LLM if available
    llm = None
    if HAS_UNIFIED_LLM:
        from unified_llm import UnifiedLLM, ModelProvider, ModelConfig, UnifiedLLMConfig
        
        try:
            # Try to create LLM with default configuration
            llm_config = UnifiedLLMConfig(
                model=ModelConfig(
                    provider=ModelProvider.LOCAL_LLAMACPP,
                    model_name="mistral-7b-instruct-v0.2",
                    temperature=0.7
                )
            )
            llm = UnifiedLLM(llm_config)
            logger.info("Initialized LLM")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM: {e}")
    
    # Create quantum interface
    interface = QuantumInterface(config, llm)
    
    # Process commands
    if args.start:
        interface.start()
        print(f"Quantum interface started. Server URL: {config.server_url}")
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("Stopping quantum interface...")
            interface.stop()
    
    elif args.stop:
        interface.stop()
        print("Quantum interface stopped.")
    
    elif args.save:
        success = interface.save_state(args.save)
        if success:
            print(f"Network state saved to {args.save}")
        else:
            print("Failed to save network state")
    
    elif args.load:
        success = interface.load_state(args.load)
        if success:
            print(f"Network state loaded from {args.load}")
        else:
            print("Failed to load network state")
    
    elif args.process_text:
        result = interface.process_text(args.process_text)
        print("Text processing result:")
        print(json.dumps(result, indent=2))
    
    elif args.process_file:
        try:
            with open(args.process_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            result = interface.process_text(text)
            print("File processing result:")
            print(json.dumps(result, indent=2))
        
        except Exception as e:
            print(f"Error processing file: {e}")
    
    elif args.create_node:
        node_type = NodeType.SEMANTIC
        if args.node_type:
            try:
                node_type = NodeType[args.node_type]
            except KeyError:
                print(f"Invalid node type: {args.node_type}")
                return
        
        with interface.state_lock:
            node_id = interface.create_node(args.create_node, node_type=node_type)
        
        if node_id:
            print(f"Node created: {node_id}")
        else:
            print("Failed to create node")
    
    elif args.create_connection:
        source_id, target_id = args.create_connection
        
        with interface.state_lock:
            success = interface.create_connection(
                source_id=source_id,
                target_id=target_id,
                strength=args.connection_strength
            )
        
        if success:
            print(f"Connection created: {source_id} -> {target_id}")
        else:
            print("Failed to create connection")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()