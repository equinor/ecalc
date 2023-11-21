from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, root_validator

from libecalc.common.errors.exceptions import EcalcError
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

    @root_validator
    def check_valid_input(cls, values):
        if not values.get("is_inlet_stream") and values.get("fluid"):
            msg = "Outgoing stream should not have a fluid model defined"
            logger.error(msg)
            raise EcalcError(msg)
        if values.get("is_inlet_stream") and not values.get("fluid"):
            msg = "Ingoing stream needs a fluid model to be define"
            logger.error(msg)
            raise EcalcError(msg)
        return values
