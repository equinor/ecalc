class InvalidStreamException(Exception):
    """Base exception for invalid stream operations."""

    pass


class NegativeMassRateException(InvalidStreamException):
    """Exception raised for negative mass rate in a stream."""

    def __init__(self, mass_rate: float):
        super().__init__(f"Mass rate must be non-negative, got {mass_rate}")


class InvalidProcessConditionsException(Exception):
    """Base exception for invalid process conditions."""

    pass


class NonPositiveTemperatureException(InvalidProcessConditionsException):
    """Exception raised when temperature is not positive."""

    def __init__(self, temperature_kelvin: float):
        super().__init__(f"Temperature must be positive, got {temperature_kelvin} K")


class NonPositivePressureException(InvalidProcessConditionsException):
    """Exception raised when pressure is not positive."""

    def __init__(self, pressure_bara: float):
        super().__init__(f"Pressure must be positive, got {pressure_bara} bara")


class StreamMixingException(InvalidStreamException):
    """Base exception for stream mixing operations."""

    pass


class EmptyStreamListException(StreamMixingException):
    """Exception raised when attempting to mix an empty list of streams."""

    def __init__(self):
        super().__init__("Cannot mix empty list of streams")


class ZeroTotalMassRateException(StreamMixingException):
    """Exception raised when the total mass rate of streams to mix is zero."""

    def __init__(self):
        super().__init__("Total mass rate cannot be zero")


class IncompatibleEoSModelsException(StreamMixingException):
    """Exception raised when mixing streams with different EoS models."""

    def __init__(self, model1, model2):
        super().__init__(f"Cannot mix streams with different EoS models: {model1} vs {model2}")
