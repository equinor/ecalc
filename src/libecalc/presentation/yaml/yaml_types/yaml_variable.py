from typing import Dict, Union

from pydantic import StringConstraints
from typing_extensions import Annotated

from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import (
    YamlDefaultDatetime,
)


class YamlSingleVariable(YamlBase):
    """
    A variable in YAML that can be set to a valid eCalc Expression
    """

    value: Expression

    def to_dto(self):
        raise NotImplementedError


YamlTimeVariable = Dict[YamlDefaultDatetime, YamlSingleVariable]

YamlVariable = Union[YamlSingleVariable, YamlTimeVariable]

YamlVariableReferenceId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")]

YamlVariables = Dict[YamlVariableReferenceId, YamlVariable]
