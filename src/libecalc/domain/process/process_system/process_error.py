from libecalc.common.errors.exceptions import EcalcError


class ProcessError(EcalcError):
    def __init__(self, reason: str = None):
        self.reason = reason
        super().__init__(title="Unable to produce an outlet stream", message=reason)


class OutsideCapacityError(ProcessError):
    def __init__(self, reason: str = "Operational point is outside capacity."):
        super().__init__(reason)


class RateTooLowError(OutsideCapacityError):
    def __init__(self, reason: str = "Rate is too low."):
        super().__init__(reason)


class RateTooHighError(OutsideCapacityError):
    def __init__(self, reason: str = "Rate is too high."):
        super().__init__(reason)
