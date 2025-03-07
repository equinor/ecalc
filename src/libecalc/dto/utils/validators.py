from datetime import date, datetime
from typing import Annotated, TypeVar, Union

from pydantic import StringConstraints

from libecalc.common.time_utils import Period, is_temporal_model
from libecalc.expression import Expression

EmissionNameStr = Annotated[str, StringConstraints(pattern=r"^\w*$")]
COMPONENT_NAME_ALLOWED_CHARS = "A-ZÆØÅa-zæøå\\d_/\\- "
COMPONENT_NAME_PATTERN = r"^[" + COMPONENT_NAME_ALLOWED_CHARS + "]*$"
ComponentNameStr = Annotated[
    str, StringConstraints(pattern=COMPONENT_NAME_PATTERN)
]  # synced with valid regexp in BE4FE

ExpressionType = Union[str, int, float, Expression]


def convert_expression(
    value: ExpressionType | dict[str | date | Period, ExpressionType] | None,
) -> Expression | dict[Period, Expression] | None:
    if value is None or isinstance(value, Expression):
        return value
    elif is_temporal_model(value):
        if all(isinstance(key, str) for key in value.keys()):
            return {
                Period(
                    start=datetime.strptime(_key.split(";")[0], "%Y-%m-%d %H:%M:%S"),
                    end=datetime.strptime(_key.split(";")[1], "%Y-%m-%d %H:%M:%S"),
                ): convert_expression(value=_value)
                for _key, _value in value.items()
            }
        if all(isinstance(key, date) for key in value.keys()):
            # convert date keys to Period keys
            model_dates = list(value.keys()) + [datetime.max.replace(microsecond=0)]
            return {
                Period(start=start_time, end=end_time): convert_expression(value=expression)
                for start_time, end_time, expression in zip(model_dates[:-1], model_dates[1:], value.values())
            }
        return {start_time: convert_expression(value=expression) for start_time, expression in value.items()}
    return Expression.setup_from_expression(value=value)


def convert_expressions(
    value: list[ExpressionType | dict[Period, ExpressionType] | None] | None,
) -> list[Expression | dict[Period, Expression] | None] | None:
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


def validate_temporal_model(model: dict[Period, TModel]) -> dict[Period, TModel]:
    if not (list(model.keys()) == sorted(model)):
        raise ValueError("Dates in a temporal model should be sorted with the earliest date first")

    return model
