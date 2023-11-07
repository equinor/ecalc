from typing import Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType


class YamlCompressorWithTurbine(YamlBase):
    compressor_model: str = Field(..., description="Reference to a compressor model", title="COMPRESSOR_MODEL")
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    power_adjustment_constant: float = Field(
        0.0,
        description="Constant to adjust power usage in MW",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    turbine_model: str = Field(..., description="Reference to a turbine model", title="TURBINE_MODEL")
    type: Literal[YamlModelType.COMPRESSOR_WITH_TURBINE] = Field(
        ...,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )

    def to_dto(self):
        raise NotImplementedError
