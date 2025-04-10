#!/usr/bin/env python3
"""
supernode_core.py

Merged implementation of the SuperNode quantum-inspired neural processing engine.
Combines vector processing, resonance-based memory, autonomous evolution, and text handling.
Optimized for CPU execution.
"""

import os
import sys
import time
import json
import numpy as np
import threading
import uuid
import logging
import math
import random
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum, auto
from dataclasses import dataclass, field
import scipy.spatial.distance as distance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SuperNodeCore")

# --- Enums and Data Structures ---

class ResonanceMode(Enum):
    """Modes for resonance calculation and evolution."""
    COSINE_SIMILARITY = auto()  # Vector similarity via cosine metric
    EUCLIDEAN_DISTANCE = auto()  # Vector similarity via Euclidean distance
    NEURAL = auto()             # Neural-inspired with activation functions
    HYBRID = auto()             # Combine similarity and neural approaches
    ADAPTIVE = auto()           # Switch modes based on state

@dataclass
class SuperNodeDNA:
    """Static configuration for a SuperNode."""
    dimension: int = 512
    initial_energy: float = 100.0
    energy_decay_rate: float = 0.02
    energy_gain_rate: float = 0.05
    resonance_mode: ResonanceMode = ResonanceMode.HYBRID
    resonance_threshold: float = 0.7
    learning_rate: float = 0.01
    plasticity: float = 0.7
    max_memory_traces: int = 100
    activation_function: str = 'tanh'
    complexity: float = 0.5
    decay_rate: float = 0.01
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    creation_time: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['resonance_mode'] = self.resonance_mode.name
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SuperNodeDNA':
        defaults = cls()
        data['resonance_mode'] = ResonanceMode[data.get('resonance_mode', 'HYBRID')]
        filtered_data = {k: data.get(k, getattr(defaults, k)) for k in defaults.__dataclass_fields__}
        return cls(**filtered_data)

@dataclass
class SuperNodeState:
    """Dynamic state of a SuperNode."""
    vector: np.ndarray
    energy: float = 100.0
    resonance: float = 0.0
    stability: float = 0.8
    last_update: float = field(default_factory=time.time)
    processing_load: float = 0.0
    attractor_states: List[np.ndarray] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['vector'] = self.vector.tolist()
        d['attractor_states'] = [state.tolist() for state in self.attractor_states]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SuperNodeState':
        vector = np.array(data.get('vector', []))
        attractor_states = [np.array(state) for state in data.get('attractor_states', [])]
        defaults = cls(vector=vector)
        filtered_data = {
            'vector': vector,
            'attractor_states': attractor_states,
            **{k: data.get(k, getattr(defaults, k)) for k in defaults.__dataclass_fields__ if k not in ['vector', 'attractor_states']}
        }
        return cls(**filtered_data)

# --- SuperNode Implementation ---

class SuperNodeCore:
    """
    Quantum-inspired processing unit for vector and text data.
    Supports resonance-based memory, adaptive transformation, and autonomous evolution.
    Optimized for CPU execution.
    """
    def __init__(self,
                 node_id: Optional[str] = None,
                 dna: Optional[SuperNodeDNA] = None,
                 initial_state: Optional[SuperNodeState] = None,
                 initial_matrix: Optional[np.ndarray] = None):
        self.id = node_id if node_id else str(uuid.uuid4())
        self.dna = dna if dna else SuperNodeDNA()
        initial_vector = np.random.normal(0, 0.1, self.dna.dimension)
        norm = np.linalg.norm(initial_vector)
        if norm > 0:
            initial_vector /= norm
        self.state = initial_state if initial_state else SuperNodeState(vector=initial_vector, energy=self.dna.initial_energy)

        # Transformation and memory
        self.transformation_matrix = initial_matrix if initial_matrix is not None and initial_matrix.shape == (self.dna.dimension, self.dna.dimension) else np.random.randn(self.dna.dimension, self.dna.dimension) * 0.1
        self.memory_traces: List[np.ndarray] = []
        self.association_matrix = np.eye(self.dna.dimension)

        # Threading and operation
        self.processing_lock = threading.RLock()
        self.running = False
        self.evolution_thread = None
        self.start_time = None

        # Activation functions
        self._activation_functions = {
            'tanh': np.tanh,
            'sigmoid': lambda x: 1 / (1 + np.exp(-x)),
            'relu': lambda x: np.maximum(0, x)
        }
        self.activation_fn = self._activation_functions.get(self.dna.activation_function, np.tanh)

        # Stats
        self.stats = {
            "processed_inputs": 0,
            "resonance_events": 0,
            "energy_fluctuations": 0,
            "stability_adjustments": 0
        }

        logger.info(f"SuperNode {self.id} initialized. Dim: {self.dna.dimension}, Mode: {self.dna.resonance_mode.name}")

    def _calculate_resonance(self, vector: np.ndarray) -> float:
        """Calculate resonance based on similarity to memory traces."""
        if not self.memory_traces:
            return 0.0
        similarities = []
        norm_vector = np.linalg.norm(vector)
        if norm_vector < 1e-9:
            return 0.0

        if self.dna.resonance_mode in [ResonanceMode.COSINE_SIMILARITY, ResonanceMode.HYBRID]:
            for trace in self.memory_traces:
                norm_trace = np.linalg.norm(trace)
                if norm_trace < 1e-9:
                    continue
                cos_dist = distance.cosine(vector, trace)
                similarities.append(1.0 - cos_dist)

        if self.dna.resonance_mode in [ResonanceMode.EUCLIDEAN_DISTANCE, ResonanceMode.HYBRID]:
            for trace in self.memory_traces:
                dist = distance.euclidean(vector, trace)
                similarities.append(math.exp(-dist * 0.1))

        if self.dna.resonance_mode == ResonanceMode.NEURAL:
            activated = self.activation_fn(vector)
            for trace in self.memory_traces:
                similarity = np.dot(activated, trace) / (np.linalg.norm(activated) * np.linalg.norm(trace) + 1e-9)
                similarities.append(similarity)

        if not similarities:
            return 0.0
        max_similarity = np.max(similarities)
        activation = (max_similarity - self.dna.resonance_threshold) / (1.0 - self.dna.resonance_threshold) if max_similarity >= self.dna.resonance_threshold else max_similarity * 0.1
        return max(0.0, min(1.0, activation))

    def _update_memory(self, vector: np.ndarray, resonance_level: float):
        """Store novel vectors in memory."""
        if resonance_level < 0.1 or abs(np.dot(self.state.vector, vector)) > self.dna.resonance_threshold:
            vector_to_store = vector.copy()
            if len(self.memory_traces) < self.dna.max_memory_traces:
                self.memory_traces.append(vector_to_store)
            else:
                self.memory_traces[random.randint(0, len(self.memory_traces) - 1)] = vector_to_store

    def _adapt_transformation(self, input_vector: np.ndarray, output_vector: np.ndarray, resonance_level: float):
        """Adapt transformation matrix using Hebbian-like learning."""
        if self.dna.learning_rate > 0:
            delta_matrix = np.outer(output_vector, input_vector)
            effective_lr = self.dna.learning_rate * (1.0 - resonance_level)
            self.transformation_matrix += effective_lr * delta_matrix
            self.transformation_matrix *= (1.0 - self.dna.learning_rate * 0.01)

    def _evolve_state(self):
        """Evolve state based on resonance mode."""
        energy_change = np.random.normal(0, 0.01)
        self.state.energy = max(0.1, min(self.state.energy + energy_change, 200.0))
        if abs(energy_change) > 0.005:
            self.stats["energy_fluctuations"] += 1

        if self.dna.resonance_mode == ResonanceMode.NEURAL:
            self.state.vector = self.activation_fn(self.association_matrix @ self.state.vector)
        elif self.dna.resonance_mode == ResonanceMode.HYBRID:
            neural = self.activation_fn(self.state.vector * self.state.energy)
            sim = self.transformation_matrix @ self.state.vector
            self.state.vector = (0.5 + 0.5 * self.state.resonance) * sim + (0.5 - 0.5 * self.state.resonance) * neural
        elif self.dna.resonance_mode == ResonanceMode.ADAPTIVE:
            self.state.vector = self.activation_fn(self.state.vector) if self.state.resonance > 0.5 else self.transformation_matrix @ self.state.vector
        else:  # COSINE_SIMILARITY or EUCLIDEAN_DISTANCE
            self.state.vector = self.transformation_matrix @ self.state.vector

        norm = np.linalg.norm(self.state.vector)
        if norm > 0:
            self.state.vector /= norm

        self.state.resonance = self._calculate_resonance(self.state.vector)
        if self.state.resonance > self.dna.resonance_threshold:
            self.stats["resonance_events"] += 1

        if hasattr(self, 'prev_state_vector'):
            change = np.linalg.norm(self.state.vector - self.prev_state_vector)
            self.state.stability *= 0.99 if change > 0.2 else 1.01 if 0.01 < change < 0.1 else 1.0
            self.state.stability = max(0.1, min(1.0, self.state.stability))
            if change > 0.2:
                self.stats["stability_adjustments"] += 1
        self.prev_state_vector = self.state.vector.copy()

        self.state.last_update = time.time()

    def _evolution_loop(self):
        """Background thread for autonomous evolution."""
        last_evolution = time.time()
        while self.running:
            if time.time() - last_evolution < 0.01:
                time.sleep(0.01)
                continue
            with self.processing_lock:
                self._evolve_state()
            last_evolution = time.time()

    def start(self):
        """Start autonomous evolution."""
        with self.processing_lock:
            if self.running:
                logger.warning("SuperNode already running")
                return
            self.running = True
            self.start_time = time.time()
            self.evolution_thread = threading.Thread(target=self._evolution_loop, daemon=True)
            self.evolution_thread.start()
            logger.info("SuperNode evolution started")

    def stop(self):
        """Stop autonomous evolution."""
        with self.processing_lock:
            if not self.running:
                logger.warning("SuperNode not running")
                return
            self.running = False
            if self.evolution_thread:
                self.evolution_thread.join(timeout=2.0)
                self.evolution_thread = None
            logger.info("SuperNode evolution stopped")

    def process(self, input_vector: np.ndarray) -> Tuple[np.ndarray, float]:
        """Process an input vector."""
        if not isinstance(input_vector, np.ndarray) or input_vector.shape != (self.dna.dimension,):
            logger.error(f"Invalid input shape. Expected ({self.dna.dimension},), got {input_vector.shape if isinstance(input_vector, np.ndarray) else type(input_vector)}")
            return np.zeros(self.dna.dimension), 0.0

        with self.processing_lock:
            start_time = time.time()
            transformed = np.dot(self.transformation_matrix, input_vector)
            resonance = self._calculate_resonance(transformed)
            output = self.activation_fn(transformed + resonance)
            self._update_memory(input_vector, resonance)
            self._adapt_transformation(input_vector, output, resonance)
            self.state.energy = max(0, self.state.energy - self.dna.energy_decay_rate + resonance * self.dna.energy_gain_rate)
            self.state.resonance = resonance
            self.state.processing_load = self.state.processing_load * 0.9 + 0.1
            self.state.last_update = time.time()
            processing_time = time.time() - start_time
            logger.debug(f"Processed vector in {processing_time:.6f}s. Resonance: {resonance:.3f}")
            self.stats["processed_inputs"] += 1
            return output, resonance

    def process_text(self, text: str) -> Tuple[np.ndarray, float]:
        """Encode and process text input."""
        vector = encode_data(text, self.dna.dimension)
        return self.process(vector)

    def get_status(self) -> Dict[str, Any]:
        """Return current status."""
        with self.processing_lock:
            uptime = time.time() - self.start_time if self.start_time else 0
            return {
                "id": self.id,
                "running": self.running,
                "uptime": uptime,
                "mode": self.dna.resonance_mode.name,
                "energy": self.state.energy,
                "resonance": self.state.resonance,
                "stability": self.state.stability,
                "memory_size": len(self.memory_traces),
                "stats": self.stats
            }

    def save_state(self, file_path: str) -> bool:
        """Save state to file."""
        with self.processing_lock:
            try:
                state_dict = {
                    "dna": self.dna.to_dict(),
                    "state": self.state.to_dict(),
                    "transformation_matrix": self.transformation_matrix.tolist(),
                    "memory_traces": [trace.tolist() for trace in self.memory_traces],
                    "association_matrix": self.association_matrix.tolist(),
                    "stats": self.stats,
                    "resonance_mode": self.dna.resonance_mode.name,
                    "timestamp": time.time()
                }
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                with open(file_path, 'w') as f:
                    json.dump(state_dict, f, indent=2)
                logger.info(f"State saved to {file_path}")
                return True
            except Exception as e:
                logger.error(f"Error saving state: {e}")
                return False

    def load_state(self, file_path: str) -> bool:
        """Load state from file."""
        with self.processing_lock:
            try:
                if not os.path.exists(file_path):
                    logger.error(f"State file not found: {file_path}")
                    return False
                with open(file_path, 'r') as f:
                    state_dict = json.load(f)
                self.dna = SuperNodeDNA.from_dict(state_dict.get("dna", {}))
                self.state = SuperNodeState.from_dict(state_dict.get("state", {}))
                self.transformation_matrix = np.array(state_dict.get("transformation_matrix", self.transformation_matrix.tolist()))
                self.memory_traces = [np.array(trace) for trace in state_dict.get("memory_traces", [])]
                self.association_matrix = np.array(state_dict.get("association_matrix", self.association_matrix.tolist()))
                self.stats = state_dict.get("stats", self.stats)
                if "resonance_mode" in state_dict:
                    self.dna.resonance_mode = ResonanceMode[state_dict["resonance_mode"]]
                logger.info(f"State loaded from {file_path}")
                return True
            except Exception as e:
                logger.error(f"Error loading state: {e}")
                return False

# --- Text Processing Utilities ---

def encode_data(text: str, dimension: int) -> np.ndarray:
    """Encode text into a vector."""
    vector = np.zeros(dimension)
    text = text.lower()
    for i, char in enumerate(set(text)):
        idx = ord(char) % (dimension // 4)
        vector[idx] += text.count(char) / len(text)
    words = text.split()
    for i, word in enumerate(set(words)):
        idx = (dimension // 4) + (abs(hash(word)) % (dimension // 4))
        if idx < dimension:
            vector[idx] += words.count(word) / len(words)
    semantic_idx = 3 * dimension // 4
    if '?' in text:
        vector[semantic_idx] = 1.0
    if '!' in text:
        vector[semantic_idx + 1] = 1.0
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector

def decode_data(vector: np.ndarray) -> str:
    """Decode vector to text approximation."""
    dimension = len(vector)
    semantic_idx = 3 * dimension // 4
    description = "Text with "
    if vector[semantic_idx] > 0.5:
        description += "question, "
    if vector[semantic_idx + 1] > 0.5:
        description += "exclamation, "
    char_section = vector[:dimension // 4]
    top_chars = [(chr(i % 128), v) for i, v in enumerate(char_section) if v > 0.01 and chr(i % 128).isprintable()]
    top_chars.sort(key=lambda x: x[1], reverse=True)
    if top_chars:
        description += f"frequent chars: {', '.join(c for c, _ in top_chars[:5])}"
    return description or "Generic text"

# --- Example Usage ---

if __name__ == "__main__":
    node = SuperNodeCore()
    node.start()
    time.sleep(1)
    text = "Hello, world! Is this working?"
    output, resonance = node.process_text(text)
    print(f"Processed text: {text}")
    print(f"Output preview (first 10): {output[:10]}")
    print(f"Resonance: {resonance:.3f}")
    print("\nStatus:")
    for k, v in node.get_status().items():
        print(f"  {k}: {v}")
    node.save_state("supernode_state.json")
    node.stop()
