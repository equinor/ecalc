from dataclasses import is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

from libecalc.common.serializable_chart import EcalcBaseModel
from libecalc.domain.process.core.results import CompressorStreamCondition

# Types that are reported multiple times across nested result structures.
# These are explicitly marked as safe to serialize repeatedly, and will
# not be detected as circular references:
SAFE_TYPES = (
    EcalcBaseModel,
    CompressorStreamCondition,
)


def is_trackable_object(obj: Any) -> bool:
    """
    Determines whether an object should be tracked to prevent circular references.

    Returns False for primitives, immutables, and known-safe types.
    Returns True only for custom objects that could participate in circular structures.
    """

    # Primitive and immutable types
    if isinstance(obj, str | int | float | bool | bytes | bytearray | complex | datetime | type(None)):
        return False

    # NumPy and pandas types are treated as value objects
    if isinstance(obj, np.generic | np.ndarray | pd.Series | pd.DataFrame):
        return False

    # Enums are serialized as value, not tracked
    if isinstance(obj, Enum):
        return False

    # Dataclasses are expanded before serialization
    if is_dataclass(obj):
        return False

    # Immutable collections
    if isinstance(obj, tuple | frozenset):
        return False

    # Known safe domain types
    if isinstance(obj, SAFE_TYPES):
        return False

    # Only track objects with mutable internal state
    return hasattr(obj, "__dict__") or hasattr(obj, "__slots__")
