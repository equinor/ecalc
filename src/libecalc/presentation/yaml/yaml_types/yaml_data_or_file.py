from typing import Annotated, Union

from pydantic import Discriminator, Field, Tag, field_validator
from typing_extensions import TypeVar

from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_validators.file_validators import (
    file_exists_validator,
)


class YamlFile(YamlBase):
    file: str = Field(
        ...,
        description="Specifies the name of an input file. See documentation for more information.",
        title="FILE",
    )

    validate_file_exists = field_validator("file", mode="after")(file_exists_validator)


def file_or_data_discriminator(data):
    if isinstance(data, YamlFile):
        return "file"
    elif not isinstance(data, dict):
        # Not json/dict and not YamlFile -> Should be TData
        return "data"

    lower_case_keys = [str(key).lower() for key in data.keys()]
    return "file" if EcalcYamlKeywords.file.lower() in lower_case_keys else "data"


TData = TypeVar("TData")

DataOrFile = Annotated[
    Union[Annotated[TData, Tag("data")], Annotated[YamlFile, Tag("file")]],
    Discriminator(file_or_data_discriminator),
]
