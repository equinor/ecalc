from datetime import datetime
from typing import Dict, Union

from libecalc.common.time_utils import convert_date_to_datetime
from libecalc.expression import Expression
from libecalc.input.yaml_types import YamlBase
from pydantic import DateError, constr
from pydantic.datetime_parse import parse_date, parse_datetime


class SingleVariable(YamlBase):
    value: Expression

    def to_dto(self):
        raise NotImplementedError


class DefaultDatetime(datetime):
    """
    PyYAML is smart and detects datetime.date and datetime.datetime differently in YAML, and parses usually
    dates to datetime.date. However, in eCalc we required datetime.datetime, and there is a subtle difference
    in behaviour between those too. Therefore we need to cast to datetime.datetime as early as possible to make
    sure eCalc behaves correctly.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.date_to_datetime

    @classmethod
    def date_to_datetime(cls, value) -> datetime:
        try:
            date = parse_date(value)
            return convert_date_to_datetime(date)
        except DateError:
            return parse_datetime(value)


TimeVariable = Dict[DefaultDatetime, SingleVariable]

Variable = Union[SingleVariable, TimeVariable]

VariableReferenceId = constr(regex=r"^[A-Za-z][A-Za-z0-9_]*$")

Variables = Dict[VariableReferenceId, Variable]
