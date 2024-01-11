from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from libecalc.common.logger import logger
from libecalc.core.models.compressor.train.fluid import FluidStream


class FluidStreamObjectForMultipleStreams(BaseModel):
    """Inlet streams needs a fluid with composition attached
    Outlet stream is what comes out of the compressor.
    """

    name: Optional[str] = None
    fluid: Optional[FluidStream] = None
    is_inlet_stream: bool
    connected_to_stage_no: int = 0
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def check_valid_input(self):
        if not self.is_inlet_stream and self.fluid:
            msg = "Outgoing stream should not have a fluid model defined"
            logger.error(msg)
            raise ValueError(msg)
        if self.is_inlet_stream and not self.fluid:
            msg = "Ingoing stream needs a fluid model to be define"
            logger.error(msg)
            raise ValueError(msg)
        return self
