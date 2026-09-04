from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_common import (
    YamlEnergyNetworkNodeBase,
    _check_non_negative,
)


class YamlConsumerBase(YamlEnergyNetworkNodeBase):
    input: Annotated[
        str,
        Field(
            title="INPUT",
            description="Source or component this receives energy from.",
        ),
    ]


class YamlElectricalConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="ElectricalConsumer")

    type: Literal["ELECTRICAL_CONSUMER"]
    load: Annotated[
        YamlExpressionType,
        Field(
            title="LOAD",
            description="Electrical power demand (MW).",
        ),
    ]

    @field_validator("load", mode="after")
    @classmethod
    def _load_non_negative(cls, v: YamlExpressionType) -> YamlExpressionType:
        return _check_non_negative(v, "LOAD")  # type: ignore[return-value]


class YamlFuelGasConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="FuelGasConsumer")

    type: Literal["FUEL_GAS_CONSUMER"]
    rate: Annotated[
        YamlExpressionType,
        Field(
            title="RATE",
            description="Fuel gas consumption rate (Sm³/d).",
        ),
    ]

    @field_validator("rate", mode="after")
    @classmethod
    def _rate_non_negative(cls, v: YamlExpressionType) -> YamlExpressionType:
        return _check_non_negative(v, "RATE")  # type: ignore[return-value]


class YamlMechanicalConsumerBase(YamlConsumerBase):
    load: Annotated[
        YamlExpressionType | None,
        Field(
            title="LOAD",
            description="Shaft power demand in MW. Mutually exclusive with PROCESS_SIMULATION.",
        ),
    ] = None
    process_simulation: Annotated[
        str | None,
        Field(
            title="PROCESS_SIMULATION",
            description="Process simulation determining the shaft power demand.",
        ),
    ] = None

    @field_validator("load", mode="after")
    @classmethod
    def _load_non_negative(
        cls,
        value: YamlExpressionType | None,
    ) -> YamlExpressionType | None:
        return _check_non_negative(value, "LOAD")

    @model_validator(mode="after")
    def check_exactly_one_demand_source(self):
        if self.load is None and self.process_simulation is None:
            raise ValueError(f"'{self.name}': either LOAD or PROCESS_SIMULATION must be specified.")
        if self.load is not None and self.process_simulation is not None:
            raise ValueError(f"'{self.name}': cannot specify both LOAD and PROCESS_SIMULATION.")
        return self


class YamlCompressor(YamlMechanicalConsumerBase):
    model_config = ConfigDict(title="Compressor")
    type: Literal["COMPRESSOR"]


class YamlPump(YamlMechanicalConsumerBase):
    model_config = ConfigDict(title="Pump")
    type: Literal["PUMP"]


class YamlDieselConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="DieselConsumer")

    type: Literal["DIESEL_CONSUMER"]
    rate: Annotated[
        YamlExpressionType,
        Field(
            title="RATE",
            description="Diesel consumption rate (l/d).",
        ),
    ]

    @field_validator("rate", mode="after")
    @classmethod
    def _rate_non_negative(cls, v: YamlExpressionType) -> YamlExpressionType:
        return _check_non_negative(v, "RATE")  # type: ignore[return-value]
