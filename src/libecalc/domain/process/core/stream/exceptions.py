class InvalidStreamException(Exception):
    """Base exception for invalid stream operations."""

    pass


class NegativeMassRateException(InvalidStreamException):
    """Exception raised for negative mass rate in a stream."""

    def __init__(self, mass_rate: float):
        super().__init__(f"Mass rate must be non-negative, got {mass_rate}")
