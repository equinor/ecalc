from __future__ import annotations

from libecalc.common.logger import logger
from libecalc.domain.component_validation_error import ModelValidationError, ProcessFluidModelValidationException
from libecalc.domain.process.compressor.core.train.fluid import FluidStream
from libecalc.presentation.yaml.validation_errors import Location


class FluidStreamObjectForMultipleStreams:
    """Inlet streams needs a fluid with composition attached
    Outlet stream is what comes out of the compressor.
    """

    def __init__(
        self,
        is_inlet_stream: bool,
        name: str | None = None,
        fluid: FluidStream | None = None,
        connected_to_stage_no: int = 0,
    ):
        self.name = name
        self.fluid = fluid
        self.is_inlet_stream = is_inlet_stream
        self.connected_to_stage_no = connected_to_stage_no
        self.check_valid_input()

    def check_valid_input(self):
        if not self.is_inlet_stream and self.fluid:
            msg = "Outgoing stream should not have a fluid model defined"
            logger.error(msg)

            raise ProcessFluidModelValidationException(
                errors=[ModelValidationError(name=self.name, location=Location([self.name]), message=str(msg))],
            )

        if self.is_inlet_stream and not self.fluid:
            msg = "Ingoing stream needs a fluid model to be defined"
            logger.error(msg)
            raise ProcessFluidModelValidationException(
                errors=[ModelValidationError(name=self.name, location=Location([self.name]), message=str(msg))],
            )
