from typing import Protocol

from libecalc.common.list.list_utils import transpose
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
)


class HasIsValid(Protocol):
    is_valid: TimeSeriesBoolean


def aggregate_is_valid(components: list[HasIsValid]) -> list[bool]:
    is_valid_arrays = [component.is_valid.values for component in components]
    return [all(is_valid_step) for is_valid_step in transpose(is_valid_arrays)]
