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
