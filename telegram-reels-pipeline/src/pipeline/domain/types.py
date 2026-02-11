"""Domain types — NewType aliases for type-safe identifiers."""

from typing import NewType

RunId = NewType("RunId", str)
AgentId = NewType("AgentId", str)
SessionId = NewType("SessionId", str)
GateName = NewType("GateName", str)
