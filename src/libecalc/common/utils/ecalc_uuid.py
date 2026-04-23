"""
Temporary UUID7 back and forwards compatible util to generate UUIDv7 for Python
UUIDv7 is only a part of the std lib from Python 3.14+
This wrapper util chooses the correct UUID util to use, based on
Python version and availability
Replace with `from uuid import uuid7` when upgrading to Python 3.14+.
"""

try:
    from uuid import UUID, uuid7  # Python 3.14+
except ImportError:
    from uuid_utils.compat import uuid7


def uuid7() -> UUID:
    return uuid7()
