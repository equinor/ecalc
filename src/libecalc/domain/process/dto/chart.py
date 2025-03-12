from typing import Literal

from libecalc.common.chart_type import ChartType
from libecalc.domain.component_validation_error import ModelValidationError, ProcessChartValueValidationException
from libecalc.presentation.yaml.validation_errors import Location


class GenericChartFromDesignPoint:
    typ: Literal[ChartType.GENERIC_FROM_DESIGN_POINT] = ChartType.GENERIC_FROM_DESIGN_POINT

    def __init__(
        self,
        polytropic_efficiency_fraction: float,
        design_rate_actual_m3_per_hour: float,
        design_polytropic_head_J_per_kg: float,
    ):
        self.polytropic_efficiency_fraction = polytropic_efficiency_fraction
        self.design_rate_actual_m3_per_hour = design_rate_actual_m3_per_hour
        self.design_polytropic_head_J_per_kg = design_polytropic_head_J_per_kg
        self._validate_polytropic_efficiency_fraction()
        self._validate_design_rate_actual_m3_per_hour()
        self._validate_design_polytropic_head_J_per_kg()

    def _validate_polytropic_efficiency_fraction(self):
        if not (0 < self.polytropic_efficiency_fraction <= 1):
            msg = f"polytropic_efficiency_fraction must be greater than 0 and less than or equal to 1. Invalid value: {self.polytropic_efficiency_fraction}"

            raise ProcessChartValueValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

    def _validate_design_rate_actual_m3_per_hour(self):
        if not isinstance(self.design_rate_actual_m3_per_hour, int | float):
            msg = "design_rate_actual_m3_per_hour must be a number"

            raise ProcessChartValueValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

        if self.design_rate_actual_m3_per_hour < 0:
            msg = f"design_rate_actual_m3_per_hour must be greater than or equal to 0. Invalid value: {self.design_rate_actual_m3_per_hour}"
            raise ProcessChartValueValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

    def _validate_design_polytropic_head_J_per_kg(self):
        if not isinstance(self.design_polytropic_head_J_per_kg, int | float):
            msg = "design_polytropic_head_J_per_kg must be a number"

            raise ProcessChartValueValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

        if self.design_polytropic_head_J_per_kg < 0:
            msg = f"design_polytropic_head_J_per_kg must be greater than or equal to 0. Invalid value: {self.design_polytropic_head_J_per_kg}"

            raise ProcessChartValueValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )


class GenericChartFromInput:
    typ: Literal[ChartType.GENERIC_FROM_INPUT] = ChartType.GENERIC_FROM_INPUT

    def __init__(self, polytropic_efficiency_fraction: float):
        self.polytropic_efficiency_fraction = polytropic_efficiency_fraction
        self._validate_polytropic_efficiency_fraction()

    def _validate_polytropic_efficiency_fraction(self):
        if not isinstance(self.polytropic_efficiency_fraction, int | float):
            msg = "polytropic_efficiency_fraction must be a number"

            raise ProcessChartValueValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

        if not (0 < self.polytropic_efficiency_fraction <= 1):
            msg = f"polytropic_efficiency_fraction must be greater than 0 and less than or equal to 1. Invalid value: {self.polytropic_efficiency_fraction}"

            raise ProcessChartValueValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )
