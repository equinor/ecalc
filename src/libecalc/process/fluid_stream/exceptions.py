from libecalc.common.errors.exceptions import EcalcError


### Fluid Composition Error
class InvalidFluidCompositionException(EcalcError):
    def __init__(self, title: str | None = None, reason: str | None = None):
        super().__init__(title=f"Invalid fluid composition: {title or ''}", message=reason or "")


## Invalid Stream
class InvalidStreamException(EcalcError):
    def __init__(self, title: str | None = None, reason: str | None = None):
        super().__init__(title=f"Invalid stream condition: {title or ''}", message=reason or "")


class NegativeMassRateException(InvalidStreamException):
    """Exception raised for negative mass rate in a stream."""

    def __init__(self, mass_rate: float):
        super().__init__(reason=f"Mass rate must be non-negative, got {mass_rate}")


class NegativeComponentFractionException(InvalidStreamException):
    def __init__(self, component_name: str, fraction: float):
        super().__init__(reason=f"Component mole fractions must be non-negative. {component_name} was {fraction} < 0")


## Stream Mixing Error
class StreamMixingException(InvalidStreamException):
    def __init__(self, reason: str | None = None):
        super().__init__(title="Invalid stream mixing", reason=reason)


class EmptyStreamListException(StreamMixingException):
    """Exception raised when attempting to mix an empty list of streams."""

    def __init__(self):
        super().__init__(reason="Cannot mix empty list of streams")


class ZeroTotalMassRateException(StreamMixingException):
    """Exception raised when the total mass rate of streams to mix is zero."""

    def __init__(self):
        super().__init__(reason="Total mass rate cannot be zero")


class IncompatibleEoSModelsException(StreamMixingException):
    """Exception raised when mixing streams with different EoS models."""

    def __init__(self, model1_name: str, model2_name: str):
        super().__init__(reason=f"Cannot mix streams with different EoS models: {model1_name} vs {model2_name}")


class IncompatibleThermoSystemProvidersException(StreamMixingException):
    """Exception raised when mixing streams with different thermo system providers."""

    def __init__(self, provider1: str, provider2: str):
        super().__init__(
            reason=f"Cannot mix streams with different thermo system providers: {provider1} vs {provider2}"
        )


## Invalid Process Conditions
class InvalidProcessConditionsException(EcalcError):
    def __init__(self, title: str | None = None, reason: str | None = None):
        super().__init__(title=f"Invalid process condition: {title or ''}", message=reason or "")


class NonPositiveTemperatureException(InvalidProcessConditionsException):
    """Exception raised when temperature is not positive."""

    def __init__(self, parameter_name: str, temperature_kelvin: float):
        super().__init__(reason=f"Temperature for {parameter_name} must be positive, got {temperature_kelvin} K")


class NonPositivePressureException(InvalidProcessConditionsException):
    """Exception raised when pressure is not positive."""

    def __init__(self, parameter_name: str, pressure_bara: float):
        super().__init__(reason=f"Pressure for {parameter_name} must be positive, got {pressure_bara} bara")
