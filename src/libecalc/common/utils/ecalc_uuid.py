"""
Temporary UUID7 back and forwards compatible util to generate UUIDv7 for Python
UUIDv7 is only a part of the std lib from Python 3.14+
Replace with `from uuid import uuid7` when upgrading to Python 3.14+.
"""

from uuid import UUID

from uuid_utils.compat import uuid7


# Instead of having to have a relation to a UUID when we need it, encapsulate it in our own ID generator
def ecalc_id_generator() -> UUID:
    return uuid7()
