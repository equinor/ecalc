from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.combustion_engine_fuel_model import validate_combustion_engine_curve
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile


class YamlTurbineCurve(YamlBase):
    model_config = ConfigDict(title="TurbineCurve")

    load: Annotated[
        list[float],
        Field(
            title="LOAD",
            description="Turbine loads [MW], strictly increasing. In a FILE, this is the LOAD column.",
        ),
    ]
    efficiency: Annotated[
        list[float],
        Field(
            title="EFFICIENCY",
            description="Turbine efficiency [fraction above 0 and up to 1] for each load. In a FILE, this is the "
            "EFFICIENCY column.",
        ),
    ]


class YamlTurbineDefinition(YamlBase):
    model_config = ConfigDict(
        title="TurbineDefinition",
        json_schema_extra={
            "examples": [
                {
                    "TYPE": "LOAD_TO_EFFICIENCY",
                    "CURVE": {
                        "LOAD": [2.352, 4.589, 6.853],
                        "EFFICIENCY": [0.138, 0.210, 0.255],
                    },
                },
                {
                    "TYPE": "LOAD_TO_EFFICIENCY",
                    "CURVE": {"FILE": "turbine_curve.csv"},
                },
            ],
        },
    )

    type: Literal["LOAD_TO_EFFICIENCY"]

    curve: Annotated[
        DataOrFile[YamlTurbineCurve],
        Field(
            title="CURVE",
            description="Load and efficiency values, given directly or in a FILE with LOAD and EFFICIENCY columns.",
        ),
    ]

    @model_validator(mode="after")
    def validate_inline_curve(self):
        if isinstance(self.curve, YamlTurbineCurve):
            try:
                validate_combustion_engine_curve(self.curve.load, self.curve.efficiency, "load-to-efficiency curve")
            except EcalcValidationException as e:
                raise ValueError(str(e)) from e
        return self
