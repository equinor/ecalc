from typing import Any

"""
Type definitions for JSON-compatible structures.

These aliases define what kinds of values are considered safe to serialize
to JSON using standard tools like `json.dumps`.

They are used throughout the Serializer system to clarify intent and improve type safety.
"""

# Primitive JSON-compatible types
JSONPrimitive = str | int | float | bool | None

# Any value that can be serialized to JSON, including nested structures.
# This includes:
# - Simple primitives (str, int, float, bool, None)
# - Lists of JSON-serializable values
# - Dicts with string keys and JSON-serializable values
JSONSerializable = JSONPrimitive | dict[str, JSONPrimitive | Any] | list[JSONPrimitive | Any]
