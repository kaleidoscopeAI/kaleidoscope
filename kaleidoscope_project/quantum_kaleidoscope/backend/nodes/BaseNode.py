# core/BaseNode.py
import logging
import random
import uuid
import json
import time
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

class BaseNode:
    """
    Foundation class for all nodes in the Kaleidoscope system.
    Includes state, basic energy dynamics, connections ("strings"),
    and methods for stress response and replication preparation.
    """

    @dataclass
    class CoreState:
        """Encapsulates the dynamic state of a node."""
        energy: float = random.uniform(50.0, 100.0) # Start with a decent energy level
        ready_to_replicate: bool = False
        dna: Dict[str, Any] = field(default_factory=lambda: {
            "mutation_rate": 0.01,
            "energy_efficiency": random.uniform(0.8, 1.2), # How well it uses energy
            "stress_resistance": random.uniform(0.8, 1.2) # How well it handles stress
        })
        metadata: Dict[str, Any] = field(default_factory=lambda: {
            "created_at": time.time(),
            "last_processed": 0.0,
            "processed_count": 0,
            "lineage": [] # Track parent IDs
        })
        stress_level: float = 0.0 # Internal stress accumulator

    def __init__(self, node_id: Optional[str] = None, core_laws: Optional[Any] = None, node_type: str = "base", parent_id: Optional[str] = None, initial_dna: Optional[Dict] = None):
        """
        Initializes a BaseNode.

        Args:
            node_id: Unique identifier. Auto-generated if None.
            core_laws: Instance of GrowthLaws governing behavior.
            node_type: String identifier for the node's type/function.
            parent_id: ID of the node from which this one replicated (if any).
            initial_dna: Specific DNA to initialize with, otherwise defaults are used/mutated.
        """
        self.id = node_id if node_id else str(uuid.uuid4())
        self.core_laws = core_laws # Should be an instance of GrowthLaws
        self.node_type = node_type
        self.state = BaseNode.CoreState()

        # Initialize DNA: Use provided, mutate from parent, or create default
        if initial_dna:
            self.state.dna = initial_dna
        elif parent_id and self.core_laws: # Mutate from parent implicitly via core_laws
             # The actual mutation happens when GrowthLaws creates DNA for the child
             pass # DNA will be set during replication process by GrowthLaws/AI_Core
        # Else: default factory DNA is used

        if parent_id:
             self.state.metadata["lineage"].append(parent_id)

        # Connections: {target_node_id: {"relationship": str, "strength": float, "stress": float}}
        self.connections: Dict[str, Dict[str, Any]] = {}
        logger.debug(f"Initialized Node: {self.id} (Type: {self.node_type}, Parent: {parent_id})")

    def process_data(self, data: Any, **kwargs) -> Dict[str, Any]:
        """
        Core data processing method (intended to be overridden by subclasses).
        Base implementation performs minimal actions and updates state.

        Args:
            data: The input data to process.
            **kwargs: Additional context or parameters.

        Returns:
            A dictionary containing processing results.
        """
        start_time = time.time()
        logger.debug(f"Node {self.id} processing data...")

        # --- Basic Processing Simulation ---
        # Simulate work by consuming energy based on data size (example)
        data_size = len(str(data)) if data else 1
        energy_cost = data_size * 0.01 / self.state.dna.get("energy_efficiency", 1.0)
        self.state.energy -= energy_cost

        # --- Subclass Override Point ---
        # Subclasses should implement their specific logic here
        processed_result = {"info": "Base processing complete", "data_echo": data}

        self.state.metadata["last_processed"] = time.time()
        self.state.metadata["processed_count"] += 1

        processing_time = time.time() - start_time
        logger.debug(f"Node {self.id} finished processing in {processing_time:.4f}s. Energy: {self.state.energy:.2f}")

        return {
            "status": "success",
            "node_id": self.id,
            "node_type": self.node_type,
            "result": processed_result,
            "energy_consumed": energy_cost,
            "processing_time": processing_time,
        }

    def apply_stress(self, stress_amount: float):
        """
        Applies external stress to the node, affecting its internal state.
        Stress resistance from DNA mitigates the effect.
        """
        resistance = self.state.dna.get("stress_resistance", 1.0)
        effective_stress = stress_amount / resistance
        self.state.stress_level += effective_stress
        # Stress impacts energy
        energy_drain = effective_stress * 0.5 # Example drain factor
        self.state.energy -= energy_drain
        logger.debug(f"Node {self.id} received stress {stress_amount:.2f}, effective: {effective_stress:.2f}. Energy: {self.state.energy:.2f}, Internal Stress: {self.state.stress_level:.2f}")
        # Potential side effects: trigger adaptation, reduce efficiency, etc. (future)


    def add_connection(self, target_node_id: str, relationship: str = "related", strength: float = 1.0, initial_stress: float = 0.0):
        """Adds or updates a connection to another node."""
        if target_node_id == self.id:
             logger.warning(f"Node {self.id} cannot connect to itself.")
             return
        self.connections[target_node_id] = {
            "relationship": relationship,
            "strength": max(0.0, min(10.0, strength)), # Clamp strength
            "stress": max(0.0, initial_stress) # Stress cannot be negative
        }
        logger.debug(f"Node {self.id} connected to {target_node_id} (Rel: {relationship}, Str: {strength:.2f})")

    def remove_connection(self, target_node_id: str):
        """Removes a connection to another node."""
        if target_node_id in self.connections:
            del self.connections[target_node_id]
            logger.debug(f"Node {self.id} disconnected from {target_node_id}")

    def update_connection_stress(self, target_node_id: str, stress_delta: float):
        """Updates the stress level on a specific connection."""
        if target_node_id in self.connections:
            conn = self.connections[target_node_id]
            conn["stress"] = max(0.0, conn["stress"] + stress_delta) # Clamp >= 0
            logger.debug(f"Node {self.id} connection to {target_node_id} stress updated by {stress_delta:.2f}. New stress: {conn['stress']:.2f}")
            # High connection stress could weaken strength or trigger node stress (future)
            if conn["stress"] > 5.0: # Example threshold
                 conn["strength"] *= 0.98 # Degrade strength slightly
                 self.apply_stress(conn["stress"] * 0.1) # Connection stress affects node

    def get_connection_ids(self) -> List[str]:
         """Returns a list of IDs of connected nodes."""
         return list(self.connections.keys())

    def get_state_summary(self) -> Dict[str, Any]:
        """Returns a concise summary of the node's state."""
        return {
            "id": self.id,
            "type": self.node_type,
            "energy": round(self.state.energy, 2),
            "stress": round(self.state.stress_level, 2),
            "ready_to_replicate": self.state.ready_to_replicate,
            "connections": len(self.connections),
            "processed_count": self.state.metadata["processed_count"],
        }

    def can_replicate(self) -> bool:
        """Checks if the node meets conditions to trigger replication signal."""
        # Check is done by GrowthLaws, this flag is set by GrowthLaws
        return self.state.ready_to_replicate

    def replicate_dna(self) -> Dict[str, Any]:
        """
        Returns a copy of the node's DNA, potentially with mutations.
        The mutation logic itself is simple here; could be expanded.
        """
        new_dna = self.state.dna.copy()
        mutation_rate = new_dna.get("mutation_rate", 0.01)

        for gene, value in new_dna.items():
            if isinstance(value, (int, float)) and random.random() < mutation_rate:
                change_factor = random.uniform(0.9, 1.1) # 10% variation
                new_dna[gene] = value * change_factor
                logger.debug(f"Node {self.id} DNA mutation in gene '{gene}': {value} -> {new_dna[gene]:.3f}")

        # Potentially add/remove genes (more complex mutation)
        # if random.random() < mutation_rate * 0.1: ...

        # Reset replication flag after DNA is copied for replication
        self.state.ready_to_replicate = False
        return new_dna

    def decay(self, base_decay_rate: float = 0.1):
        """Applies natural energy decay and stress reduction over time."""
        # Energy decay
        decay_amount = base_decay_rate * (1 / self.state.dna.get("energy_efficiency", 1.0))
        self.state.energy -= decay_amount
        self.state.energy = max(0, self.state.energy) # Cannot go below zero

        # Stress reduction (nodes recover over time)
        stress_recovery = self.state.stress_level * 0.05 # Recover 5% of current stress
        self.state.stress_level = max(0.0, self.state.stress_level - stress_recovery)

        if self.state.energy <= 0:
             logger.warning(f"Node {self.id} has depleted its energy.")
             # Consider adding a 'dead' state or signalling for removal
