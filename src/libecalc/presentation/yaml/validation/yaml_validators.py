from datetime import date, datetime
from typing import Dict, List, Optional, TypeVar, Union

from pydantic import constr

from libecalc.common.time_utils import is_temporal_model
from libecalc.expression import Expression

EmissionNameStr = constr(regex=r"^\w*$")
COMPONENT_NAME_ALLOWED_CHARS = "A-ZÆØÅa-zæøå\\d_/\\- "
ComponentNameStr = constr(regex=r"^[" + COMPONENT_NAME_ALLOWED_CHARS + "]*$")  # synced with valid regexp in BE4FE

ExpressionType = Union[str, int, float, Expression]
TModel = TypeVar("TModel")


def convert_expression(
    value: Optional[Union[ExpressionType, Dict[date, ExpressionType]]]
) -> Optional[Union[Expression, Dict[date, Expression]]]:
    if value is None or isinstance(value, Expression):
        return value
    elif is_temporal_model(value):
        return {start_time: convert_expression(value=expression) for start_time, expression in value.items()}
    return Expression.setup_from_expression(value=value)


def convert_expressions(
    values: Optional[List[Optional[Union[ExpressionType, Dict[date, ExpressionType]]]]]
) -> Optional[List[Optional[Union[Expression, Dict[date, Expression]]]]]:
    if values is None:
        return values
    if not isinstance(values, list):
        return convert_expression(value=values)
    else:
        return [convert_expression(value=value) for value in values]


def validate_temporal_model(model: Dict[datetime, TModel]) -> Dict[datetime, TModel]:
    if not (list(model.keys()) == sorted(model)):
        raise ValueError("Dates in a temporal model should be sorted with the earliest date first")

    return model