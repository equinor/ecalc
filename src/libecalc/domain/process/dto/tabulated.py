from typing import Literal

from libecalc.common.consumer_type import ConsumerType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import InvalidColumnException
from libecalc.domain.component_validation_error import (
    ModelValidationError,
    ProcessEqualLengthValidationException,
    ProcessHeaderValidationException,
)
from libecalc.domain.process.dto.base import ConsumerFunction
from libecalc.domain.process.dto.sampled import EnergyModelSampled
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.presentation.yaml.validation_errors import Location


class TabulatedData(EnergyModelSampled):
    typ: Literal[EnergyModelType.TABULATED] = EnergyModelType.TABULATED

    def __init__(
        self,
        headers: list[str],
        data: list[list[float]],
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
    ):
        super().__init__(headers, data, energy_usage_adjustment_constant, energy_usage_adjustment_factor)
        self.validate_headers()
        self.validate_data()

    def validate_headers(self):
        is_valid_headers = len(self.headers) > 0 and ("FUEL" in self.headers or "POWER" in self.headers)
        if not is_valid_headers:
            msg = "TABULAR facility input type data must have a 'FUEL' or 'POWER' header"

            raise ProcessHeaderValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

    def validate_data(self):
        lengths = [len(lst) for lst in self.data]
        if len(set(lengths)) > 1:
            problematic_vectors = [(i, len(lst)) for i, lst in enumerate(self.data)]
            msg = f"TABULAR facility input type data should have equal number of datapoints for all headers. Found lengths: {problematic_vectors}"

            raise ProcessEqualLengthValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )
        for column_index, header in enumerate(self.headers):
            for row_index, value in enumerate(self.data[column_index]):
                try:
                    float(value)
                except ValueError as e:
                    raise InvalidColumnException(
                        header=header, message=f"Got non-numeric value '{value}'.", row=row_index
                    ) from e


class Variables:
    def __init__(self, name: str, expression: Expression):
        self.name = name
        self.expression = convert_expression(expression)


class TabulatedConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.TABULATED] = ConsumerType.TABULATED

    def __init__(
        self,
        model: TabulatedData,
        energy_usage_type: EnergyUsageType,
        variables: list[Variables],
        power_loss_factor: Expression | None = None,
        condition: Expression | None = None,
    ):
        super().__init__(ConsumerType.TABULATED, energy_usage_type, power_loss_factor)
        self.model = model
        self.variables = variables
        self.power_loss_factor = convert_expression(power_loss_factor) if power_loss_factor else None
        self.condition = convert_expression(condition) if condition else None
