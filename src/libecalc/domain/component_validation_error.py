class DomainValidationException(Exception):
    def __init__(self, message: str = None):
        self.message = message
        super().__init__(message)


class ComponentValidationException(DomainValidationException):
    pass


class ProcessEqualLengthValidationException(DomainValidationException):
    pass


class ProcessNegativeValuesValidationException(DomainValidationException):
    pass


class ProcessMissingVariableValidationException(DomainValidationException):
    pass


class ProcessChartTypeValidationException(DomainValidationException):
    pass


class ProcessChartValueValidationException(DomainValidationException):
    pass


class ProcessPressureRatioValidationException(DomainValidationException):
    pass


class ProcessDischargePressureValidationException(DomainValidationException):
    pass


class ProcessDirectConsumerFunctionValidationException(DomainValidationException):
    pass


class ProcessHeaderValidationException(DomainValidationException):
    pass


class ProcessTurbineEfficiencyValidationException(DomainValidationException):
    pass


class ProcessCompressorEfficiencyValidationException(DomainValidationException):
    pass


class ProcessFluidModelValidationException(DomainValidationException):
    pass


class GeneratorSetHeaderValidationException(DomainValidationException):
    pass


class GeneratorSetEqualLengthValidationException(DomainValidationException):
    pass
