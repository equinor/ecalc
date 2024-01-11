from datetime import date, datetime
from typing import Dict, List, Optional, TypeVar, Union

from pydantic import StringConstraints
from typing_extensions import Annotated

from libecalc.common.time_utils import is_temporal_model
from libecalc.expression import Expression

EmissionNameStr = Annotated[str, StringConstraints(pattern=r"^\w*$")]
COMPONENT_NAME_ALLOWED_CHARS = "A-ZÆØÅa-zæøå\\d_/\\- "
COMPONENT_NAME_PATTERN = r"^[" + COMPONENT_NAME_ALLOWED_CHARS + "]*$"
ComponentNameStr = Annotated[
    str, StringConstraints(pattern=COMPONENT_NAME_PATTERN)
]  # synced with valid regexp in BE4FE

ExpressionType = Union[str, int, float, Expression]


def convert_expression(
    value: Optional[Union[ExpressionType, Dict[date, ExpressionType]]]
) -> Optional[Union[Expression, Dict[date, Expression]]]:
    if value is None or isinstance(value, Expression):
        return value
    elif is_temporal_model(value):
        return {start_time: convert_expression(value=expression) for start_time, expression in value.items()}
    return Expression.setup_from_expression(value=value)


def convert_expressions(
    value: Optional[List[Optional[Union[ExpressionType, Dict[date, ExpressionType]]]]]
) -> Optional[List[Optional[Union[Expression, Dict[date, Expression]]]]]:
    if value is None:
        return value
    if not isinstance(value, list):
        return convert_expression(value=value)
    else:
        return [convert_expression(value=value) for value in value]


def uppercase_user_defined_category(value):
    if value is not None and isinstance(value, str):
        return value.upper()
    elif value is not None and is_temporal_model(value):
        return {timestep: category.upper() for timestep, category in value.items()}
    return value


TModel = TypeVar("TModel")


def validate_temporal_model(model: Dict[datetime, TModel]) -> Dict[datetime, TModel]:
    if not (list(model.keys()) == sorted(model)):
        raise ValueError("Dates in a temporal model should be sorted with the earliest date first")

    return model
