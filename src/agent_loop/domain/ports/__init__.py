"""Domain ports: Interfaces for external dependencies.

Ports define the contracts that adapters must implement.
See [AR1c] for abstraction requirements.
"""

from agent_loop.domain.ports.memory_store import MemoryStore

__all__ = [
    "MemoryStore",
]
