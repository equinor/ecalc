"""
Custom pydantic type to allow for serialization and validation of ndarray
"""

from typing import Annotated

import numpy as np
from pydantic import BeforeValidator, PlainSerializer


def nd_array_custom_before_validator(x):
    # custom before validation logic
    if isinstance(x, list):
        return np.asarray(x)
    return x


def nd_array_custom_serializer(x):
    # custom serialization logic
    return str(x)


PydanticNDArray = Annotated[
    np.ndarray,
    BeforeValidator(nd_array_custom_before_validator),
    PlainSerializer(nd_array_custom_serializer, return_type=str),
]
