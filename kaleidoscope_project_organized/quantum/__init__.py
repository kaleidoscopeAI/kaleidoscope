"""
Quantum Module for Kaleidoscope AI
==================================

This package contains components related to the quantum-inspired synchronization,
simulation, and orchestration within the Kaleidoscope AI system.

It includes:
- QuantumNetworkServer: Manages WebSocket connections and quantum states (from quantum_server.py).
- QuantumNetworkClient: Client agent connecting to the quantum server.
- QuantumSynchronizationProtocol: Handles sync between Kaleidoscope fleet and quantum network.
- QuantumOrchestrationHub: Middleware for visualization integration.
"""

# Expose key classes and functions for easier access
from .quantum_sync_protocol import QuantumSynchronizationProtocol
from .quantum_client import QuantumNetworkClient
from .quantum_hub import QuantumOrchestrator, QuantumKaleidoscopeServer
# Assuming quantum_server.py defines QuantumNetworkServer (adjust if needed)
# from .quantum_server import QuantumNetworkServer

__all__ = [
    "QuantumSynchronizationProtocol",
    "QuantumNetworkClient",
    "QuantumOrchestrator",
    "QuantumKaleidoscopeServer",
    # "QuantumNetworkServer", # Uncomment if quantum_server.py defines this
]

__version__ = "0.1.0"
