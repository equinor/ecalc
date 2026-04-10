from typing import Annotated, Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    TurbineModelReference,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType

CompressorModelReference = str  # Specific type is handled when referencing the CompressorWithTurbine type, since allowed compressor models varies between components.


class YamlCompressorWithTurbine(YamlBase):
    compressor_model: Annotated[
        CompressorModelReference,
        Field(description="Reference to a compressor model", title="COMPRESSOR_MODEL"),
    ]
    name: Annotated[
        ModelName,
        Field(
            description="Name of the model. See documentation for more information.",
            title="NAME",
        ),
    ]
    power_adjustment_constant: Annotated[
        float,
        Field(
            description="Constant to adjust power usage in MW",
            title="POWER_ADJUSTMENT_CONSTANT",
        ),
    ] = 0.0
    power_adjustment_factor: Annotated[
        float,
        Field(
            description="Factor to adjust power usage in MW",
            title="POWER_ADJUSTMENT_FACTOR",
        ),
    ] = 1.0
    turbine_model: Annotated[
        TurbineModelReference,
        Field(description="Reference to a turbine model", title="TURBINE_MODEL"),
    ]
    type: Annotated[
        Literal[YamlModelType.COMPRESSOR_WITH_TURBINE],
        Field(
            description="Defines the type of model. See documentation for more information.",
            title="TYPE",
        ),
    ]

    def to_dto(self):
        raise NotImplementedError
