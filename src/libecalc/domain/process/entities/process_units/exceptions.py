from __future__ import annotations


class ProcessUnitException(Exception):
    """Base exception for all process unit operations."""

    pass


class NoInletStreamException(ProcessUnitException):
    """Exception raised when trying to access inlet stream that hasn't been set."""

    def __init__(self):
        super().__init__("No inlet stream has been set for this process unit")
