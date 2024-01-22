"""
Custom pydantic type to allow for serialization and validation of ndarray
"""
import numpy as np
from pydantic import BeforeValidator, PlainSerializer
from typing_extensions import Annotated


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
