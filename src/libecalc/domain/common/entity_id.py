from __future__ import annotations

import uuid
from typing import Protocol
from uuid import UUID


class ID(Protocol):
    """Minimal interface for any entity identifier in the domain layer."""

    def get_name(self) -> str:
        """Get the human-readable name."""
        ...

    def get_uuid(self) -> UUID:
        """Get the unique identifier."""
        ...


class SimpleEntityID:
    """Simple entity ID implementation for standalone use cases and tests."""

    def __init__(self, name: str):
        self._name = name
        self._uuid = uuid.uuid4()

    def get_name(self) -> str:
        return self._name

    def get_uuid(self) -> UUID:
        return self._uuid

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"SimpleEntityID(name='{self._name}', uuid='{self._uuid}')"
