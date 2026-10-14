from typing import Annotated

from pydantic import ConfigDict, Field, model_validator

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.motor_efficiency_model import validate_motor_curve
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile


class YamlMotorCurve(YamlBase):
    model_config = ConfigDict(title="MotorCurve")

    load: Annotated[
        list[float],
        Field(
            title="LOAD",
            description="Mechanical output [MW], strictly increasing. In a FILE, this is the LOAD column.",
        ),
    ]
    efficiency: Annotated[
        list[float],
        Field(
            title="EFFICIENCY",
            description="Motor efficiency [fraction above 0 and up to 1] for each load. In a FILE, this is the "
            "EFFICIENCY column.",
        ),
    ]


class YamlMotorDefinition(YamlBase):
    model_config = ConfigDict(
        title="MotorDefinition",
        json_schema_extra={
            "examples": [
                {"CURVE": {"LOAD": [1, 3, 5], "EFFICIENCY": [0.90, 0.95, 0.96]}},
                {"CURVE": {"FILE": "motor_curve.csv"}},
            ],
        },
    )

    curve: Annotated[
        DataOrFile[YamlMotorCurve],
        Field(
            title="CURVE",
            description="Load and efficiency values, given directly or in a FILE with LOAD and EFFICIENCY columns.",
        ),
    ]

    @model_validator(mode="after")
    def validate_inline_curve(self):
        if isinstance(self.curve, YamlMotorCurve):
            try:
                validate_motor_curve(self.curve.load, self.curve.efficiency)
            except EcalcValidationException as e:
                raise ValueError(str(e)) from e
        return self
