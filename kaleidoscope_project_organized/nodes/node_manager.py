# core/NodeManager.py
import logging
import random
import time
from typing import Dict, List, Any, Optional, Tuple, Type

# Avoid circular import for type hinting
from .BaseNode import BaseNode # Assuming BaseNode is in the same directory

logger = logging.getLogger(__name__)

class NodeManager:
    """
    Manages the lifecycle and interactions of all nodes in the system.
    Handles registration, lookup, connections, and applying network-wide effects.
    """

    def __init__(self, max_nodes: int = 1000):
        """
        Initializes the NodeManager.

        Args:
            max_nodes: The maximum number of nodes allowed in the system.
        """
        self.nodes: Dict[str, BaseNode] = {} # {node_id: node_object}
        self.max_nodes = max_nodes
        self.node_creation_times: Dict[str, float] = {} # Track creation time for aging
        logger.info(f"NodeManager initialized with max_nodes = {max_nodes}")

    def register_node(self, node: BaseNode) -> bool:
        """
        Registers a node with the manager if space is available.

        Args:
            node: The BaseNode instance to register.

        Returns:
            True if registration was successful, False otherwise.
        """
        if len(self.nodes) >= self.max_nodes:
            logger.warning(f"Max node limit ({self.max_nodes}) reached. Cannot register node {node.id}.")
            # Optional: Implement culling of oldest/weakest nodes here
            # self.cull_nodes(1) # Example: remove one node to make space
            # if len(self.nodes) >= self.max_nodes: # Check again after culling
            #     return False
            return False

        if node.id in self.nodes:
            logger.warning(f"Attempted to register duplicate node ID: {node.id}. Ignoring.")
            return False

        self.nodes[node.id] = node
        self.node_creation_times[node.id] = time.time()
        logger.info(f"Registered node: {node.id} (Type: {node.node_type}). Total nodes: {len(self.nodes)}")
        return True

    def unregister_node(self, node_id: str) -> Optional[BaseNode]:
        """
        Unregisters a node and cleans up its connections from other nodes.

        Args:
            node_id: The ID of the node to unregister.

        Returns:
            The unregistered node object if found, otherwise None.
        """
        node_to_remove = self.nodes.pop(node_id, None)
        if node_to_remove:
            self.node_creation_times.pop(node_id, None)
            logger.info(f"Unregistered node: {node_id}. Total nodes: {len(self.nodes)}")

            # Remove connections pointing *to* this node from others
            nodes_to_update = []
            for other_node in self.nodes.values():
                if node_id in other_node.connections:
                     nodes_to_update.append(other_node)

            for other_node in nodes_to_update:
                 other_node.remove_connection(node_id)
                 logger.debug(f"Removed connection from {other_node.id} to unregistered node {node_id}")

            return node_to_remove
        else:
            logger.warning(f"Attempted to unregister non-existent node ID: {node_id}")
            return None

    def get_node(self, node_id: str) -> Optional[BaseNode]:
        """Retrieves a node by its ID."""
        return self.nodes.get(node_id)

    def get_all_nodes(self) -> List[BaseNode]:
        """Returns a list of all managed node objects."""
        return list(self.nodes.values())

    def get_node_count(self) -> int:
        """Gets the total number of registered nodes."""
        return len(self.nodes)

    def get_all_statuses(self, summary: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Gets the status of all registered nodes.

        Args:
            summary: If True, returns concise summary using node.get_state_summary().
                     If False, returns more detailed state (can be large).

        Returns:
            A dictionary mapping node IDs to their status dictionaries.
        """
        statuses = {}
        for node_id, node in self.nodes.items():
            if summary:
                statuses[node_id] = node.get_state_summary()
            else:
                # Potentially large, use with caution
                try:
                     statuses[node_id] = node.state.__dict__.copy() # Get state attributes
                     statuses[node_id]['connections'] = node.connections.copy() # Add connections info
                except Exception as e:
                     logger.error(f"Error getting detailed state for node {node_id}: {e}")
                     statuses[node_id] = {"error": "Failed to retrieve detailed state"}
        return statuses

    def find_nodes_by_type(self, node_type: str) -> List[BaseNode]:
        """Finds nodes of a specific type."""
        return [node for node in self.nodes.values() if node.node_type == node_type]

    def find_nodes_by_capability(self, capability: str) -> List[BaseNode]:
         """Finds nodes that declare a specific capability (requires capability mechanism on nodes)."""
         # This assumes nodes have a 'capabilities' attribute or similar
         return [node for node in self.nodes.values() if hasattr(node, 'capabilities') and capability in node.capabilities]


    def connect_nodes(self, node_id1: str, node_id2: str, relationship: str = "related", strength: float = 1.0, bidirectional: bool = True):
        """
        Establishes a connection between two nodes.

        Args:
            node_id1: ID of the first node.
            node_id2: ID of the second node.
            relationship: Description of the connection type.
            strength: Initial strength of the connection.
            bidirectional: If True, adds the connection on both nodes.
        """
        node1 = self.get_node(node_id1)
        node2 = self.get_node(node_id2)

        if node1 and node2:
            node1.add_connection(node_id2, relationship, strength)
            if bidirectional:
                node2.add_connection(node_id1, relationship, strength) # Add reciprocal connection
            logger.info(f"Nodes connected: {node_id1} {'<-->' if bidirectional else '-->'} {node_id2} (Rel: {relationship}, Str: {strength:.2f})")
        else:
            missing_nodes = []
            if not node1: missing_nodes.append(node_id1)
            if not node2: missing_nodes.append(node_id2)
            logger.warning(f"Cannot connect nodes. Missing nodes: {', '.join(missing_nodes)}")

    def apply_global_stress(self, stress_amount: float):
        """
        Applies a uniform stress amount to all nodes in the network.
        """
        if stress_amount == 0: return # No-op optimization
        logger.info(f"Applying global stress of {stress_amount:.2f} to {len(self.nodes)} nodes.")
        for node in self.nodes.values():
            if node.state.energy > 0: # Only affect active nodes
                node.apply_stress(stress_amount)

    def apply_targeted_stress(self, stress_pattern: Dict[str, float]):
        """
        Applies specific stress amounts to targeted nodes based on a pattern.

        Args:
            stress_pattern: A dictionary {node_id: stress_amount}.
                            Nodes not in the pattern are unaffected.
        """
        logger.info(f"Applying targeted stress pattern to {len(stress_pattern)} nodes.")
        for node_id, stress_amount in stress_pattern.items():
            node = self.get_node(node_id)
            if node and node.state.energy > 0:
                node.apply_stress(stress_amount)
            elif node_id not in self.nodes:
                 logger.debug(f"Node {node_id} not found for targeted stress.")


    def propagate_connection_stress(self, propagation_factor: float = 0.1):
        """
        Simulates stress propagating through connections. High stress on a
        connection can induce stress on the connected nodes.
        """
        logger.debug("Propagating connection stress...")
        node_stress_updates: Dict[str, float] = {} # Accumulate stress before applying

        for node in self.nodes.values():
             if node.state.energy <= 0: continue
             for target_id, conn_data in node.connections.items():
                 connection_stress = conn_data.get("stress", 0.0)
                 if connection_stress > 1.0: # Only propagate significant stress
                     induced_stress = connection_stress * propagation_factor
                     # Add stress to both self and target based on this connection
                     node_stress_updates[node.id] = node_stress_updates.get(node.id, 0.0) + induced_stress
                     node_stress_updates[target_id] = node_stress_updates.get(target_id, 0.0) + induced_stress
                     # Optional: Degrade connection strength due to high stress
                     # conn_data["strength"] *= (1.0 - (connection_stress * 0.01))

        # Apply accumulated stress
        if node_stress_updates:
             self.apply_targeted_stress(node_stress_updates)


    def get_weakest_nodes(self, count: int = 1) -> List[BaseNode]:
         """ Finds nodes with the lowest energy levels. """
         if not self.nodes: return []
         sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.state.energy)
         return sorted_nodes[:count]

    def get_oldest_nodes(self, count: int = 1) -> List[BaseNode]:
         """ Finds the nodes that were created earliest. """
         if not self.node_creation_times: return []
         sorted_ids = sorted(self.node_creation_times.items(), key=lambda item: item[1]) # Sort by timestamp
         oldest_ids = [nid for nid, ts in sorted_ids[:count]]
         return [self.nodes[nid] for nid in oldest_ids if nid in self.nodes]

    def cull_nodes(self, count: int = 1, strategy: str = 'weakest'):
         """
         Removes nodes based on a specified strategy (e.g., 'weakest', 'oldest').
         Use carefully, as this removes nodes permanently.
         """
         logger.warning(f"Culling {count} nodes using strategy: {strategy}")
         nodes_to_cull: List[BaseNode] = []
         if strategy == 'weakest':
              nodes_to_cull = self.get_weakest_nodes(count)
         elif strategy == 'oldest':
              nodes_to_cull = self.get_oldest_nodes(count)
         else:
              logger.error(f"Unknown culling strategy: {strategy}")
              return

         for node in nodes_to_cull:
              logger.info(f"Culling node {node.id} (Energy: {node.state.energy:.2f}, Age: {time.time() - self.node_creation_times.get(node.id, 0):.0f}s)")
              self.unregister_node(node.id)


    def get_network_statistics(self) -> Dict[str, Any]:
         """ Calculates basic statistics about the node network. """
         num_nodes = len(self.nodes)
         if num_nodes == 0:
              return {"node_count": 0}

         total_energy = 0
         total_stress = 0
         total_connections = 0
         node_types_count = {}
         active_nodes = 0

         for node in self.nodes.values():
              if node.state.energy > 0:
                   active_nodes += 1
                   total_energy += node.state.energy
                   total_stress += node.state.stress_level
                   total_connections += len(node.connections)
                   node_types_count[node.node_type] = node_types_count.get(node.node_type, 0) + 1

         avg_energy = total_energy / active_nodes if active_nodes > 0 else 0
         avg_stress = total_stress / active_nodes if active_nodes > 0 else 0
         # Each connection is counted twice (once per node), so divide by 2
         avg_connections = (total_connections / active_nodes) if active_nodes > 0 else 0

         return {
              "node_count": num_nodes,
              "active_nodes": active_nodes,
              "avg_energy": round(avg_energy, 2),
              "total_energy": round(total_energy, 2),
              "avg_stress": round(avg_stress, 2),
              "avg_connections": round(avg_connections, 2),
              "node_type_distribution": node_types_count,
         }
