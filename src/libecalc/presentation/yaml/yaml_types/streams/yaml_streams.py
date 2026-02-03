import enum
from typing import Self

from pydantic import Field, model_validator

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlRate

StreamRef = str
FluidModelReference = str


class YamlInletRateUnit(str, enum.Enum):
    SM3_PER_DAY = "SM3_PER_DAY"
    KG_PER_HOUR = "KG_PER_HOUR"
    KMOL_PER_HOUR = "KMOL_PER_HOUR"  # For future molar rate support


class YamlInletStreamRate(YamlRate):
    unit: YamlInletRateUnit = Field(
        ...,
        title="UNIT",
        description="Rate unit. SM3_PER_DAY for standard volume, KG_PER_HOUR for mass, KMOL_PER_HOUR for molar rate.",
    )


class YamlInletStream(YamlBase):
    """
    Represents an inlet stream definition that can be referenced by process system and stream distribution.
    """

    name: StreamRef = Field(
        ...,
        title="NAME",
        description="Unique name of the inlet stream.",
    )
    fluid_model: FluidModelReference = Field(
        ...,
        title="FLUID_MODEL",
        description="Reference to a fluid model (e.g. defined in MODELS/FLUID_MODELS elsewhere).",
    )

    temperature: YamlExpressionType | None = Field(
        None,
        title="TEMPERATURE",
        description="Temperature in K. Optional; defaults to standard temperature if omitted.",
    )
    pressure: YamlExpressionType | None = Field(
        None,
        title="PRESSURE",
        description="Pressure in Pa. Optional; defaults to standard pressure if omitted.",
    )

    rate: YamlInletStreamRate = Field(
        ...,
        title="RATE",
        description="Rate with unit + value.",
    )


class YamlInletStreams(YamlBase):
    inlet_streams: list[YamlInletStream] = Field(
        ...,
        title="INLET_STREAMS",
        description="List of inlet streams available to process systems and stream distribution.",
    )

    @model_validator(mode="after")
    def _validate_unique_names(self) -> Self:
        names = [s.name for s in self.inlet_streams]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(f"Duplicate inlet stream NAME(s): {sorted(duplicates)}")
        return self
