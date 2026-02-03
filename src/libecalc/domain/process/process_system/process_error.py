from libecalc.common.errors.exceptions import EcalcError


class ProcessError(EcalcError):
    def __init__(self, message: str = None):
        self.message = message
        super().__init__(title=None, message=message)


class OutsideCapacityError(ProcessError):
    pass


class RateTooLowError(OutsideCapacityError):
    pass


class RateTooHighError(OutsideCapacityError):
    pass
