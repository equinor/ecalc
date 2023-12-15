from __future__ import annotations

from typing import Optional

try:
    from pydantic.v1 import BaseModel, root_validator
except ImportError:
    from pydantic import BaseModel, root_validator

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.logger import logger
from libecalc.core.models.compressor.train.fluid import FluidStream


class FluidStreamObjectForMultipleStreams(BaseModel):
    """Inlet streams needs a fluid with composition attached
    Outlet stream is what comes out of the compressor.
    """

    name: Optional[str]
    fluid: Optional[FluidStream]
    is_inlet_stream: bool
    connected_to_stage_no: int = 0

    class Config:
        arbitrary_types_allowed = True

    @root_validator(skip_on_failure=True)
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
