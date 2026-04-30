from libecalc.common.errors.exceptions import EcalcError


class EcalcValidationException(EcalcError):
    def __init__(self, message: str = None):
        self.message = message
        super().__init__(title=None, message=message)


class ProcessEqualLengthValidationException(EcalcValidationException):
    pass


class ProcessNegativeValuesValidationException(EcalcValidationException):
    pass


class ProcessMissingVariableValidationException(EcalcValidationException):
    pass


class ProcessChartTypeValidationException(EcalcValidationException):
    pass


class ProcessPressureRatioValidationException(EcalcValidationException):
    pass


class ProcessDischargePressureValidationException(EcalcValidationException):
    pass


class ProcessHeaderValidationException(EcalcValidationException):
    pass


class ProcessTurbineEfficiencyValidationException(EcalcValidationException):
    pass


class ProcessCompressorEfficiencyValidationException(EcalcValidationException):
    pass


class GeneratorSetHeaderValidationException(EcalcValidationException):
    pass


class GeneratorSetEqualLengthValidationException(EcalcValidationException):
    pass
