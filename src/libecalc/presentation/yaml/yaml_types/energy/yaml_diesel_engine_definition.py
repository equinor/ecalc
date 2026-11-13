from typing import Annotated

from pydantic import ConfigDict, Field, model_validator

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.combustion_engine_fuel_model import validate_combustion_engine_curve
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineCurve
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile
from libecalc.presentation.yaml.yaml_types.yaml_version import V5, yaml_element_lifecycle


class YamlDieselEngineDefinition(YamlBase):
    model_config = ConfigDict(
        title="DieselEngineDefinition",
        json_schema_extra={
            **yaml_element_lifecycle(available_since=V5),
            "examples": [
                {
                    "CURVE": {
                        "LOAD": [2.352, 4.589, 6.853],
                        "EFFICIENCY": [0.138, 0.210, 0.255],
                    },
                },
                {
                    "CURVE": {"FILE": "diesel_engine_curve.csv"},
                },
            ],
        },
    )

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
                validate_combustion_engine_curve(self.curve.load, self.curve.efficiency, "diesel engine")
            except EcalcValidationException as e:
                raise ValueError(str(e)) from e
        return self
