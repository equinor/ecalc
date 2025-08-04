from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, model_validator

from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel


class FluidStreamType(str, Enum):
    INGOING = "INGOING"
    OUTGOING = "OUTGOING"


class MultipleStreamsAndPressureStream(BaseModel):
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
