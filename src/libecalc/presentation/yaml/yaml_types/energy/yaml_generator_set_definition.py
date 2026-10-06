from typing import Annotated

from pydantic import ConfigDict, Field, model_validator

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.generator_set_fuel_model import validate_generator_set_curve
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile


class YamlGeneratorSetCurve(YamlBase):
    model_config = ConfigDict(title="GeneratorSetCurve")

    power: Annotated[
        list[float],
        Field(
            title="POWER",
            description="Electrical power [MW], strictly increasing. In a FILE, this is the POWER column.",
        ),
    ]
    fuel: Annotated[
        list[float],
        Field(
            title="FUEL",
            description="Fuel gas rate [Sm3/day] for each power. In a FILE, this is the FUEL column.",
        ),
    ]


class YamlGeneratorSetDefinition(YamlBase):
    model_config = ConfigDict(
        title="GeneratorSetDefinition",
        json_schema_extra={
            "examples": [
                {"CURVE": {"POWER": [0, 5, 10, 15], "FUEL": [0, 25000, 48000, 70000]}},
                {"CURVE": {"FILE": "generator_set_curve.csv"}},
            ],
        },
    )

    curve: Annotated[
        DataOrFile[YamlGeneratorSetCurve],
        Field(
            title="CURVE",
            description="Power and fuel values, given directly or in a FILE with POWER and FUEL columns.",
        ),
    ]

    @model_validator(mode="after")
    def validate_inline_curve(self):
        if isinstance(self.curve, YamlGeneratorSetCurve):
            try:
                validate_generator_set_curve(self.curve.power, self.curve.fuel)
            except EcalcValidationException as e:
                raise ValueError(str(e)) from e
        return self
