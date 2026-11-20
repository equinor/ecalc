from pydantic import ConfigDict, Field

from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.presentation.yaml.yaml_types import YamlBase

type PumpReference = str


class YamlPump(YamlBase):
    """A physical pump. Pump process units in PUMP_PIPELINES reference it by name."""

    model_config = ConfigDict(title="Pump")

    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Unique name of the physical pump.",
    )
    alias: str | None = Field(
        default=None,
        title="ALIAS",
        description="Optional alias for the pump.",
    )
