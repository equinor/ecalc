from __future__ import annotations

import numpy as np

from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.core.models.pump import PumpModel
from libecalc.core.result import EcalcModelResult
from libecalc.core.result import results as core_results
from libecalc.domain.infrastructure.energy_components.base import BaseConsumerWithoutOperationalSettings
from libecalc.domain.stream_conditions import Pressure, StreamConditions


class Pump(BaseConsumerWithoutOperationalSettings):
    def __init__(self, id: str, pump_model: PumpModel):
        self.id = id
        self._pump_model = pump_model

    def get_max_rate(self, inlet_stream: StreamConditions, target_pressure: Pressure) -> list[float]:
        """
        For each timestep, get the maximum rate that this pump can handle, given
        the operational settings given, such as in -and outlet pressures and fluid density (current conditions)

        Args:
            inlet_stream: the inlet stream
            target_pressure: the target pressure
        """
        return self._pump_model.get_max_standard_rate(
            suction_pressures=np.asarray([inlet_stream.pressure.value]),
            discharge_pressures=np.asarray([target_pressure.value]),
            fluid_density=np.asarray([inlet_stream.density.value]),
        ).tolist()[0]

    def evaluate(
        self,
        streams: list[StreamConditions],
    ) -> EcalcModelResult:
        inlet_streams = streams[:-1]
        outlet_stream = streams[-1]

        model_result = self._pump_model.evaluate_streams(
            inlet_streams=inlet_streams,
            outlet_stream=outlet_stream,
        )

        # Mixing all input rates to get total rate passed through compressor. Used when reporting streams.
        total_requested_inlet_stream = StreamConditions.mix_all(inlet_streams)
        total_requested_inlet_stream.name = "Total inlet"
        current_period = total_requested_inlet_stream.period

        outlet_stream.rate = total_requested_inlet_stream.rate

        component_result = core_results.PumpResult(
            id=self.id,
            periods=Periods([current_period]),
            power=TimeSeriesStreamDayRate(
                values=model_result.power,
                periods=Periods([current_period]),
                unit=model_result.power_unit,
            ).fill_nan(0.0),
            energy_usage=TimeSeriesStreamDayRate(
                values=model_result.energy_usage,
                periods=Periods([current_period]),
                unit=model_result.energy_usage_unit,
            ).fill_nan(0.0),
            inlet_liquid_rate_m3_per_day=TimeSeriesStreamDayRate(
                values=model_result.rate,
                periods=Periods([current_period]),
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
            inlet_pressure_bar=TimeSeriesFloat(
                values=model_result.suction_pressure,
                periods=Periods([current_period]),
                unit=Unit.BARA,
            ),
            outlet_pressure_bar=TimeSeriesFloat(
                values=model_result.discharge_pressure,
                periods=Periods([current_period]),
                unit=Unit.BARA,
            ),
            operational_head=TimeSeriesFloat(
                values=model_result.operational_head,
                periods=Periods([current_period]),
                unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
            ),
            is_valid=TimeSeriesBoolean(values=model_result.is_valid, periods=Periods([current_period]), unit=Unit.NONE),
            streams=[
                TimeSeriesStreamConditions.from_stream_condition(total_requested_inlet_stream),
                *[
                    TimeSeriesStreamConditions.from_stream_condition(inlet_stream_conditions)
                    for inlet_stream_conditions in inlet_streams
                ],
                TimeSeriesStreamConditions.from_stream_condition(outlet_stream),
            ],
        )

        return EcalcModelResult(
            component_result=component_result,
            sub_components=[],
            models=[
                core_results.PumpModelResult(
                    name="N/A",  # No context available to populate model name
                    periods=Periods([current_period]),
                    is_valid=TimeSeriesBoolean(
                        periods=Periods([current_period]),
                        values=model_result.is_valid,
                        unit=Unit.NONE,
                    ),
                    power=TimeSeriesStreamDayRate(
                        periods=Periods([current_period]),
                        values=model_result.power,
                        unit=model_result.power_unit,
                    )
                    if model_result.power is not None
                    else None,
                    energy_usage=TimeSeriesStreamDayRate(
                        periods=Periods([current_period]),
                        values=model_result.energy_usage,
                        unit=model_result.energy_usage_unit,
                    ),
                    inlet_liquid_rate_m3_per_day=model_result.rate,
                    inlet_pressure_bar=model_result.suction_pressure,
                    outlet_pressure_bar=model_result.discharge_pressure,
                    operational_head=model_result.operational_head,
                )
            ],
        )
