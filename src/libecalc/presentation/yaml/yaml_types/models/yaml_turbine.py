from typing import Literal

from pydantic import ConfigDict, Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType


class YamlTurbine(YamlBase):
    model_config = ConfigDict(
        title="TURBINE",
        json_schema_extra={
            "examples": [
                {
                    "NAME": "compressor_train_turbine",
                    "TYPE": YamlModelType.TURBINE,
                    "LOWER_HEATING_VALUE": "38 # MJ/Sm3",
                    "TURBINE_LOADS": [0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767],
                    "TURBINE_EFFICIENCIES": [0, 0.138, 0.210, 0.255, 0.286, 0.310, 0.328, 0.342, 0.353, 0.360, 0.362],
                    "POWER_ADJUSTMENT_CONSTANT": 10,
                }
            ],
        },
    )

    name: ModelName = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.TURBINE] = Field(
        ...,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    lower_heating_value: float = Field(
        ...,
        description="Lower heating value [MJ/Sm3] of fuel. Lower heating value is also known as net calorific value",
        title="LOWER_HEATING_VALUE",
    )
    turbine_loads: list[float] = Field(
        ...,
        description="Load values [MW] in load vs efficiency table for turbine. Number of elements must correspond to number of elements in TURBINE_EFFICIENCIES. See documentation for more information.",
        title="TURBINE_LOADS",
    )
    turbine_efficiencies: list[float] = Field(
        ...,
        description="Efficiency values in load vs efficiency table for turbine. Efficiency is given as fraction between 0 and 1 corresponding to 0-100%. Number of elements must correspond to number of elements in TURBINE_LOADS. See documentation for more information.",
        title="TURBINE_EFFICIENCIES",
    )
    power_adjustment_constant: float = Field(
        0,
        description="Constant to adjust power usage in MW",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    power_adjustment_factor: float = Field(
        1.0,
        description="Factor to adjust power usage in MW",
        title="POWER_ADJUSTMENT_FACTOR",
    )

    def to_dto(self):
        raise NotImplementedError
