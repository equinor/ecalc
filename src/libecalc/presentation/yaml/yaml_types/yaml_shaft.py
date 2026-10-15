from pydantic import ConfigDict, Field

from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.presentation.yaml.yaml_types import YamlBase

type ShaftReference = str


class YamlShaft(YamlBase):
    model_config = ConfigDict(title="Shaft")

    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Unique name of the shaft.",
    )
