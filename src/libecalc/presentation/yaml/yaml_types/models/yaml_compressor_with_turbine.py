from typing import Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    TurbineModelReference,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType

CompressorModelReference = str  # Specific type is handled when referencing the CompressorWithTurbine type, since allowed compressor models varies between components.


class YamlCompressorWithTurbine(YamlBase):
    compressor_model: CompressorModelReference = Field(
        ..., description="Reference to a compressor model", title="COMPRESSOR_MODEL"
    )
    name: ModelName = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    power_adjustment_constant: float = Field(
        0.0,
        description="Constant to adjust power usage in MW",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    power_adjustment_factor: float = Field(
        1.0,
        description="Factor to adjust power usage in MW",
        title="POWER_ADJUSTMENT_FACTOR",
    )
    turbine_model: TurbineModelReference = Field(..., description="Reference to a turbine model", title="TURBINE_MODEL")
    type: Literal[YamlModelType.COMPRESSOR_WITH_TURBINE] = Field(
        ...,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )

    def to_dto(self):
        raise NotImplementedError
