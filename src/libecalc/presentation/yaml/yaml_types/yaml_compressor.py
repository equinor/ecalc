from pydantic import ConfigDict, Field

from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.presentation.yaml.yaml_types import YamlBase

type CompressorReference = str


class YamlCompressor(YamlBase):
    """A physical compressor. Pipeline compressor slots and COMPRESSOR_SAMPLED units reference it by name."""

    model_config = ConfigDict(title="Compressor")

    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Unique name of the physical compressor, e.g. its equipment tag.",
    )
    alias: str | None = Field(
        default=None,
        title="ALIAS",
        description="Optional alias for the compressor, e.g. 'RIA'.",
    )
