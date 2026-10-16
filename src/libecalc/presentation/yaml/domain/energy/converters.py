from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from libecalc.common.time_utils import Period
from libecalc.energy import Converter, EfficiencyConversion, SampledConversion
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_optional_energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TimeSeriesSampledConverterFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        input_energy_type: type[Energy],
        output_energy_type: type[Energy],
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
        curve: Callable[[float], float] = lambda value: value,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id, capacity=capacity)
        self._input_energy_type = input_energy_type
        self._output_energy_type = output_energy_type
        self._curve = curve

    @property
    def curve(self) -> Callable[[float], float]:
        return self._curve

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> Converter:
        (incoming_connection,) = incoming_connections
        period: Period | None = extra.get("period")
        return Converter(
            name=self.get_name(),
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            input_energy_type=self._input_energy_type,
            output_energy_type=self._output_energy_type,
            conversion=SampledConversion(self._curve),
            energy_unit_id=self.get_id(),
            capacity=resolve_optional_energy(
                self.capacity,
                self._output_energy_type,
                period=period,
                description=f"Capacity for '{self.get_name()}'",
            ),
        )


class TimeSeriesEfficiencyConverterFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        input_energy_type: type[Energy],
        output_energy_type: type[Energy],
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
        efficiency: TimeSeriesExpression,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id, capacity=capacity)
        self._input_energy_type = input_energy_type
        self._output_energy_type = output_energy_type
        self._efficiency = efficiency

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> Converter:
        (incoming_connection,) = incoming_connections
        period: Period = extra["period"]
        return Converter(
            name=self.get_name(),
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            input_energy_type=self._input_energy_type,
            output_energy_type=self._output_energy_type,
            conversion=EfficiencyConversion(self._efficiency.get_value(period)),
            energy_unit_id=self.get_id(),
            capacity=resolve_optional_energy(
                self.capacity,
                self._output_energy_type,
                period=period,
                description=f"Capacity for '{self.get_name()}'",
            ),
        )
