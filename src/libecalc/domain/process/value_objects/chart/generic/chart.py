from typing import Literal

from libecalc.common.chart_type import ChartType
from libecalc.domain.component_validation_error import ProcessChartValueValidationException


class GenericChartFromInput:
    typ: Literal[ChartType.GENERIC_FROM_INPUT] = ChartType.GENERIC_FROM_INPUT

    def __init__(self, polytropic_efficiency_fraction: float):
        self.polytropic_efficiency_fraction = polytropic_efficiency_fraction
        self._validate_polytropic_efficiency_fraction()

    def _validate_polytropic_efficiency_fraction(self):
        if not isinstance(self.polytropic_efficiency_fraction, int | float):
            msg = "polytropic_efficiency_fraction must be a number"

            raise ProcessChartValueValidationException(message=str(msg))

        if not (0 < self.polytropic_efficiency_fraction <= 1):
            msg = f"polytropic_efficiency_fraction must be greater than 0 and less than or equal to 1. Invalid value: {self.polytropic_efficiency_fraction}"

            raise ProcessChartValueValidationException(message=str(msg))
