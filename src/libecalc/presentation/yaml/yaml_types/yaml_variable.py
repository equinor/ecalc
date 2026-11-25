from typing import Annotated, Union

from pydantic import GetJsonSchemaHandler, StringConstraints
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

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


class NoAdditionalProperties:
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema["additionalProperties"] = False
        return json_schema


YamlTimeVariable = dict[YamlDefaultDatetime, YamlSingleVariable]

YamlVariable = Union[YamlSingleVariable, YamlTimeVariable]

YamlVariableReferenceId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")]

YamlVariables = Annotated[
    dict[YamlVariableReferenceId, YamlVariable],
    NoAdditionalProperties(),
]
