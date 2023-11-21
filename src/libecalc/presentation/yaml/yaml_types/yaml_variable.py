from datetime import datetime
from typing import Dict, Union

from pydantic import DateError, StringConstraints
from pydantic.datetime_parse import parse_date, parse_datetime
from typing_extensions import Annotated

from libecalc.common.time_utils import convert_date_to_datetime
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types import YamlBase


class YamlSingleVariable(YamlBase):
    """
    A variable in YAML that can be set to a valid eCalc Expression
    """

    value: Expression

    def to_dto(self):
        raise NotImplementedError


class YamlDefaultDatetime(datetime):
    """
    PyYAML is smart and detects datetime.date and datetime.datetime differently in YAML, and parses usually
    dates to datetime.date. However, in eCalc we required datetime.datetime, and there is a subtle difference
    in behaviour between those too. Therefore we need to cast to datetime.datetime as early as possible to make
    sure eCalc behaves correctly.
    """

    @classmethod
    # TODO[pydantic]: We couldn't refactor `__get_validators__`, please create the `__get_pydantic_core_schema__` manually.
    # Check https://docs.pydantic.dev/latest/migration/#defining-custom-types for more information.
    def __get_validators__(cls):
        yield cls.date_to_datetime

    @classmethod
    def date_to_datetime(cls, value) -> datetime:
        """
        Handles both datetimes and dates supported formats, and converts them to
        datetime.datetime internally to avoid problems with mixing datetime.date and datetime.datetime
        :param value: string with a PyYAML supported date or datetime format
        :return: the corresponding datetime.datetime. datetime.date will have HH:MM:SS set to 00:00:00
        """
        try:
            date = parse_date(value)
            return convert_date_to_datetime(date)
        except DateError:
            return parse_datetime(value)


YamlTimeVariable = Dict[YamlDefaultDatetime, YamlSingleVariable]

YamlVariable = Union[YamlSingleVariable, YamlTimeVariable]

YamlVariableReferenceId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")]

YamlVariables = Dict[YamlVariableReferenceId, YamlVariable]
