from typing import Annotated, Any

from pydantic import BeforeValidator, WithJsonSchema

from libecalc.common.version import Version


def convert_str_to_version(x: Any):
    if isinstance(x, str):
        return Version.from_string(x)
    return x


YamlVersion = Annotated[
    Version,
    BeforeValidator(convert_str_to_version),
    WithJsonSchema({"type": "string"}),
]
