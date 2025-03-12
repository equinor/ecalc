from libecalc.domain.component_validation_error import ModelValidationError, ProcessEqualLengthValidationException
from libecalc.domain.process.dto.base import EnergyModel
from libecalc.presentation.yaml.validation_errors import Location


class EnergyModelSampled(EnergyModel):
    def __init__(
        self,
        headers: list[str],
        data: list[list[float]],
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
    ):
        super().__init__(energy_usage_adjustment_constant, energy_usage_adjustment_factor)
        self.headers = headers
        self.data = data
        self.validate_headers()
        self.validate_data()

    def validate_headers(self):
        # Ensure the number of headers equals the number of vectors
        if len(self.headers) != len(self.data):
            msg = (
                f"The number of headers ({len(self.headers)}) must equal the number of data vectors ({len(self.data)})"
            )

            raise ProcessEqualLengthValidationException(
                errors=[ModelValidationError(name="", location=Location([""]), message=str(msg))],
            )

    def validate_data(self):
        # Ensure all vectors in data have equal length
        lengths = [len(lst) for lst in self.data]
        if len(set(lengths)) > 1:
            problematic_vectors = [(i, len(lst)) for i, lst in enumerate(self.data)]
            msg = f"All vectors in data must have equal length. Found lengths: {problematic_vectors}"

            raise ProcessEqualLengthValidationException(
                errors=[ModelValidationError(name="", location=Location([""]), message=str(msg))],
            )
