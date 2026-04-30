from libecalc.common.errors.exceptions import EcalcError
from libecalc.process.process_pipeline.process_unit import ProcessUnitId


class ProcessError(EcalcError):
    def __init__(self, reason: str | None = None):
        self.reason = reason
        super().__init__(title="Unable to produce an outlet stream", message=reason or "")


class OutsideCapacityError(ProcessError):
    def __init__(self, reason: str = "Operational point is outside capacity."):
        super().__init__(reason)


class RateTooLowError(OutsideCapacityError):
    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        actual_rate: float | None = None,
        boundary_rate: float | None = None,
        reason: str = "Rate is too low.",
    ):
        self.actual_rate = actual_rate
        self.boundary_rate = boundary_rate
        self.process_unit_id = process_unit_id
        super().__init__(reason)


class RateTooHighError(OutsideCapacityError):
    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        actual_rate: float | None = None,
        boundary_rate: float | None = None,
        reason: str = "Rate is too high.",
    ):
        self.actual_rate = actual_rate
        self.boundary_rate = boundary_rate
        self.process_unit_id = process_unit_id
        super().__init__(reason)
