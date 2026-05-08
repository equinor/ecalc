from collections.abc import Mapping


class CompressorThermodynamicCalculationError(Exception):
    """Raised when compressor thermodynamics cannot produce a usable state."""

    def __init__(
        self,
        operation: str,
        reason: str,
        details: Mapping[str, object | None] | None = None,
    ):
        self.operation = operation
        self.reason = reason
        self.details = {name: value for name, value in (details or {}).items() if value is not None}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        message = f"Compressor thermodynamic calculation failed during {self.operation}: {self.reason}"
        if not self.details:
            return message

        formatted_details = ", ".join(f"{name}={value}" for name, value in self.details.items())
        return f"{message} Context: {formatted_details}."


class CompressorOutletCalculationError(CompressorThermodynamicCalculationError):
    """Raised when compressor outlet thermodynamics cannot produce a usable state."""
