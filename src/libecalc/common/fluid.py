from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from libecalc.common.fluid_stream_type import FluidStreamType
from libecalc.common.string.string_utils import to_camel_case
from libecalc.domain.process.entities.fluid_stream.eos_model import EoSModel
from libecalc.domain.process.entities.fluid_stream.fluid_composition import FluidComposition


class EcalcBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class FluidModel(EcalcBaseModel):
    eos_model: EoSModel
    composition: FluidComposition


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
