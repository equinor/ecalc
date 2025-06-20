from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from libecalc.common.fluid_stream_type import FluidStreamType
from libecalc.common.string.string_utils import to_camel_case
from libecalc.domain.process.value_objects.fluid_stream.eos_model import EoSModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_composition import FluidComposition


class EcalcBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class FluidModel(EcalcBaseModel):
    eos_model: EoSModel
    composition: FluidComposition


class FluidStreamCommon(FluidModel):
    pressure_bara: float
    temperature_kelvin: float
    density_kg_per_m3: float
    kappa: float
    z: float

    @classmethod
    def from_fluid_domain_object(cls, fluid_stream) -> FluidStreamCommon:
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
    fluid_model: FluidModel | None = None

    @model_validator(mode="after")
    def validate_stream(self):
        stream_name, stream_type, stream_fluid_model = (
            self.name,
            self.typ,
            self.fluid_model,
        )
        if stream_type == FluidStreamType.INGOING and not isinstance(stream_fluid_model, FluidModel):
            raise ValueError(f"Stream {stream_name} is of type {stream_type} and needs a fluid model to be defined")
        if stream_type == FluidStreamType.OUTGOING and isinstance(stream_fluid_model, FluidModel):
            raise ValueError(f"Stream {stream_name} is of type {stream_type} and should not have a fluid model defined")
        return self
