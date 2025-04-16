from libecalc.common.errors.exceptions import InvalidColumnException
from libecalc.domain.component_validation_error import (
    ModelValidationError,
    ProcessEqualLengthValidationException,
    ProcessHeaderValidationException,
)
from libecalc.presentation.yaml.validation_errors import Location


class GeneratorSetValidator:
    def __init__(self, headers: list[str], data: list[list[float]], typ: str):
        self.headers = headers
        self.data = data
        self.typ = typ

    def validate(self):
        self.validate_headers()
        self.validate_data()

    def validate_headers(self):
        is_valid_headers = len(self.headers) == 2 and "FUEL" in self.headers and "POWER" in self.headers
        if not is_valid_headers:
            msg = "Sampled generator set data should have a 'FUEL' and 'POWER' header"

            raise ProcessHeaderValidationException(
                errors=[ModelValidationError(name=self.typ, location=Location([self.typ]), message=str(msg))],
            )

    def validate_data(self):
        # Ensure data is column-wise.
        # Check if the number of data columns matches the number of headers.
        if len(self.data) != len(self.headers):
            raise ProcessEqualLengthValidationException(
                errors=[
                    ModelValidationError(
                        name=self.typ,
                        location=Location([self.typ]),
                        message=f"Data should have {len(self.headers)} columns, but got {len(self.data)}.",
                    )
                ]
            )

        # Check if all columns in the data have the same number of rows.
        lengths = [len(lst) for lst in self.data]
        if len(set(lengths)) > 1:
            problematic_vectors = [(i, len(lst)) for i, lst in enumerate(self.data)]
            msg = f"Sampled generator set data should have equal number of datapoints for FUEL and POWER. Found lengths: {problematic_vectors}"

            raise ProcessEqualLengthValidationException(
                errors=[ModelValidationError(name=self.typ, location=Location([self.typ]), message=str(msg))],
            )

        # Iterate through each column and validate that all values are numeric.
        for column_index, header in enumerate(self.headers):
            for row_index, value in enumerate(self.data[column_index]):
                try:
                    float(value)
                except ValueError as e:
                    raise InvalidColumnException(
                        header=header, message=f"Got non-numeric value '{value}'.", row=row_index
                    ) from e
