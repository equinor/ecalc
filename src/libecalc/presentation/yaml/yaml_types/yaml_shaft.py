from pydantic import ConfigDict, Field

from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.yaml_compressor import CompressorReference

type ShaftReference = str


class YamlShaft(YamlBase):
    model_config = ConfigDict(title="Shaft")

    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Unique name of the shaft.",
    )
    compressors: list[CompressorReference] = Field(
        default_factory=list,
        title="COMPRESSORS",
        description="Names of the compressors in COMPRESSORS that sit on this shaft and run at its speed. A compressor "
        "placed in a process pipeline must be on a shaft. A DRIVE_TRAIN on this shaft drives all of them.",
    )
