from typing import Annotated, Any, Literal, TypeVar, Union

from pydantic import Discriminator, Tag

from libecalc.common.errors.exceptions import InvalidDateException
from libecalc.common.time_utils import is_temporal_model
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import (
    YamlDefaultDatetime,
)


def discriminate_temporal_model(v: Any) -> Literal["single", "temporal"]:
    """

    Args:
        v: data to validate, can be both validated pydantic models and to-be-validated dict/Any

    Returns:

    """
    if isinstance(v, dict):
        try:
            if is_temporal_model(v):
                return "temporal"
            else:
                return "single"
        except InvalidDateException:
            # is_temporal_model validation of dates failed -> pass data to temporal validation and handle error there
            return "temporal"

    # No need to check whether temporal or not as a temporal model always is a dict
    return "single"


TModel = TypeVar("TModel")
YamlTemporalModel = Annotated[
    Union[
        Annotated[TModel, Tag("single")],
        Annotated[
            dict[YamlDefaultDatetime, TModel],
            Tag("temporal"),
        ],
    ],
    Discriminator(discriminate_temporal_model),
]
