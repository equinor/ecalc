from datetime import date, datetime
from typing import Dict, Union

from pydantic import AfterValidator, StringConstraints
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


YamlDefaultDatetime = Union[datetime, Annotated[date, AfterValidator(convert_date_to_datetime)]]

YamlTimeVariable = Dict[YamlDefaultDatetime, YamlSingleVariable]

YamlVariable = Union[YamlSingleVariable, YamlTimeVariable]

YamlVariableReferenceId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")]

YamlVariables = Dict[YamlVariableReferenceId, YamlVariable]
