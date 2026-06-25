"""Back-compat shim.

The MLX engine moved to server/backends/mlx.py (it's now one backend behind the
EngineLike port) and the backend-neutral GenChunk to server/core/ports.py. This
keeps `from server.engine import Engine / GenChunk` working; new code should use
server.backends.make_engine (the factory) and server.core.ports.GenChunk.
"""

from .backends.mlx import MlxEngine
from .core.ports import GenChunk

Engine = MlxEngine  # historical name for the MLX backend

__all__ = ["Engine", "GenChunk", "MlxEngine"]
