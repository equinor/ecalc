from __future__ import annotations

import math

from libecalc.common.errors.exceptions import InvalidColumnException
from libecalc.common.time_utils import Period
from libecalc.domain.resource import Resource
from libecalc.ecalc_model.equipment.equipment_id import EquipmentId
from libecalc.energy.energy_types import MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.energy.models.sampled_compressor import SampledCompressor
from libecalc.energy.models.sampled_compressor_factory import SampledCompressorFactory
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnit
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression

SHAFT_POWER = "SHAFT_POWER"
RATE = "RATE"
SUCTION_PRESSURE = "SUCTION_PRESSURE"
DISCHARGE_PRESSURE = "DISCHARGE_PRESSURE"

# Earlier versions of COMPRESSOR_SAMPLED read FUEL and/or POWER, and generated a turbine for both.
_REPLACED_COLUMNS = ("FUEL", "POWER")


def _value_at(expression: TimeSeriesExpression | None, period: Period) -> float | None:
    return expression.get_value(period) if expression is not None else None


class TimeSeriesCompressorSampled(TimeSeriesEnergyUnit):
    """
    A compressor whose shaft power is looked up in a resource from rate, suction pressure and/or discharge pressure,
    consuming shaft power from its driver.

    The resource must have a SHAFT_POWER column, and a column for exactly those variables that are given.
    """

    def __init__(
        self,
        *,
        compressor_equipment_id: EquipmentId,
        name: str,
        file: str,
        resource: Resource,
        energy_unit_id: EnergyUnitId | None = None,
        rate: TimeSeriesExpression | None = None,
        suction_pressure: TimeSeriesExpression | None = None,
        discharge_pressure: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.compressor_equipment_id = compressor_equipment_id
        self.file = file
        self.resource = resource
        self.rate = rate
        self.suction_pressure = suction_pressure
        self.discharge_pressure = discharge_pressure
        self._model = self._create_model()

    def _create_model(self) -> SampledCompressor:
        headers = {header.lower(): header for header in self.resource.get_headers()}
        for replaced in _REPLACED_COLUMNS:
            if replaced.lower() in headers:
                raise InvalidColumnException(
                    header=headers[replaced.lower()],
                    message=f"Column '{replaced}' is not supported, give {SHAFT_POWER} instead. Model a fuel or power "
                    f"driven compressor with a GAS_TURBINE or an ELECTRICAL_MOTOR as INPUT.",
                )

        shaft_power_values = self.resource.get_float_column(SHAFT_POWER)
        variable_values: dict[str, list[float] | None] = {}
        for header, expression in (
            (RATE, self.rate),
            (SUCTION_PRESSURE, self.suction_pressure),
            (DISCHARGE_PRESSURE, self.discharge_pressure),
        ):
            if expression is not None:
                variable_values[header] = self.resource.get_float_column(header)
            elif header.lower() in headers:
                raise InvalidColumnException(
                    header=headers[header.lower()],
                    message=f"The file has a column for {header}, so {header} must be given.",
                )
            else:
                variable_values[header] = None

        return SampledCompressorFactory.create(
            energy_usage_values=shaft_power_values,
            rate_values=variable_values[RATE],
            suction_pressure_values=variable_values[SUCTION_PRESSURE],
            discharge_pressure_values=variable_values[DISCHARGE_PRESSURE],
        )

    def get_input_energy_type(self) -> type[MechanicalPower]:
        return MechanicalPower

    def get_shaft_power(self, period: Period) -> MechanicalPower:
        shaft_power = self._model.evaluate(
            rate=_value_at(self.rate, period),
            suction_pressure=_value_at(self.suction_pressure, period),
            discharge_pressure=_value_at(self.discharge_pressure, period),
        ).energy_usage
        if math.isnan(shaft_power):
            raise InvalidEnergyNetworkInputError(
                f"Sampled compressor '{self.get_name()}' input for period {period} is outside the model's sampled "
                f"range."
            )
        return MechanicalPower(value=shaft_power)
