from __future__ import annotations

from typing import Optional

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.types import EoSModel, FluidStreamType
from pydantic import Field, root_validator


class FluidComposition(EcalcBaseModel):
    water: float = Field(0.0, ge=0.0)
    nitrogen: float = Field(0.0, ge=0.0)
    CO2: float = Field(0.0, ge=0.0)
    methane: float = Field(0.0, ge=0.0)
    ethane: float = Field(0.0, ge=0.0)
    propane: float = Field(0.0, ge=0.0)
    i_butane: float = Field(0.0, ge=0.0)
    n_butane: float = Field(0.0, ge=0.0)
    i_pentane: float = Field(0.0, ge=0.0)
    n_pentane: float = Field(0.0, ge=0.0)
    n_hexane: float = Field(0.0, ge=0.0)


class FluidModel(EcalcBaseModel):
    eos_model: EoSModel
    composition: FluidComposition


class FluidStream(FluidModel):
    pressure_bara: float
    temperature_kelvin: float
    density_kg_per_m3: float
    kappa: float
    z: float

    @classmethod
    def from_fluid_domain_object(cls, fluid_stream) -> FluidStream:
        return cls(
            eos_model=fluid_stream.fluid_model.eos_model,
            composition=fluid_stream.fluid_model.composition,
            pressure_bara=fluid_stream.pressure_bara,
            temperature_kelvin=fluid_stream.temperature_kelvin,
            density_kg_per_m3=fluid_stream.density,
            kappa=fluid_stream.kappa,
            z=fluid_stream.z,
        )


class MultipleStreamsAndPressureStream(EcalcBaseModel):
    name: str
    typ: FluidStreamType
    fluid_model: Optional[FluidModel]

    @root_validator
    def validate_stream(cls, values):
        stream_name, stream_type, stream_fluid_model = (
            values.get("name"),
            values.get("typ"),
            values.get("fluid_model"),
        )
        if stream_type == FluidStreamType.INGOING and not isinstance(stream_fluid_model, FluidModel):
            raise ValueError(f"Stream {stream_name} is of type {stream_type} and needs a fluid model to be defined")
        if stream_type == FluidStreamType.OUTGOING and isinstance(stream_fluid_model, FluidModel):
            raise ValueError(f"Stream {stream_name} is of type {stream_type} and should not have a fluid model defined")
        return values
