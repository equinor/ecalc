from typing import Any, Dict, TypeVar, Union

from pydantic import Discriminator, Tag
from typing_extensions import Annotated, Literal

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
        if is_temporal_model(v):
            return "temporal"
        else:
            return "single"

    # No need to check whether temporal or not as a temporal model always is a dict
    return "single"


TModel = TypeVar("TModel")
YamlTemporalModel = Annotated[
    Union[
        Annotated[TModel, Tag("single")],
        Annotated[
            Dict[YamlDefaultDatetime, TModel],
            Tag("temporal"),
        ],
    ],
    Discriminator(discriminate_temporal_model),
]
