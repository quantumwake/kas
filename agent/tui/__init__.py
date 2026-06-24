"""kas TUI package — the textual front-end.

Decomposed from the original 1.5k-line agent/tui.py (v3 Phase 3). `AgentApp` is
the composition root; the rest of the package holds the pieces it wires together
(widgets, the AgentIO adapter, the ambient fx, the command registry, stats, and
the worker loops). External code imports `AgentApp` from here, unchanged.
"""

from .app import AgentApp

__all__ = ["AgentApp"]
