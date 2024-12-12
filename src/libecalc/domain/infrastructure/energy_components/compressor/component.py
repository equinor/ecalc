from __future__ import annotations

import numpy as np

from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesStreamDayRate,
)
from libecalc.core.models.compressor import CompressorModel
from libecalc.core.result import EcalcModelResult
from libecalc.core.result import results as core_results
from libecalc.domain.infrastructure.energy_components.base import BaseConsumerWithoutOperationalSettings
from libecalc.domain.stream_conditions import Pressure, StreamConditions


class Compressor(BaseConsumerWithoutOperationalSettings):
    def __init__(self, id: str, compressor_model: CompressorModel):
        self.id = id
        self._compressor_model = compressor_model

    def get_max_rate(self, inlet_stream: StreamConditions, target_pressure: Pressure) -> float:
        """
        Get the maximum rate that this compressor can handle, given in -and outlet pressures.

        Args:
            inlet_stream: the inlet stream
            target_pressure: the target pressure
        """
        return self._compressor_model.get_max_standard_rate(
            suction_pressures=np.asarray([inlet_stream.pressure.value]),
            discharge_pressures=np.asarray([target_pressure.value]),
        ).tolist()[0]

    def evaluate(
        self,
        streams: list[StreamConditions],
    ) -> EcalcModelResult:
        inlet_streams = streams[:-1]
        outlet_stream = streams[-1]

        model_result = self._compressor_model.evaluate_streams(
            inlet_streams=inlet_streams,
            outlet_stream=outlet_stream,
        )

        # Mixing all input rates to get total rate passed through compressor. Used when reporting streams.
        total_requested_inlet_stream = StreamConditions.mix_all(inlet_streams)
        total_requested_inlet_stream.name = "Total inlet"
        current_period = total_requested_inlet_stream.period

        outlet_stream.rate = total_requested_inlet_stream.rate

        energy_usage = TimeSeriesStreamDayRate(
            values=model_result.energy_usage,
            periods=Periods([current_period]),
            unit=model_result.energy_usage_unit,
        )

        component_result = core_results.CompressorResult(
            periods=Periods([current_period]),
            power=TimeSeriesStreamDayRate(
                values=model_result.power,
                periods=Periods([current_period]),
                unit=model_result.power_unit,
            ).fill_nan(0.0),
            energy_usage=energy_usage.fill_nan(0.0),
            is_valid=TimeSeriesBoolean(values=model_result.is_valid, periods=Periods([current_period]), unit=Unit.NONE),
            id=self.id,
            recirculation_loss=TimeSeriesStreamDayRate(
                values=model_result.recirculation_loss,
                periods=Periods([current_period]),
                unit=Unit.MEGA_WATT,
            ),
            rate_exceeds_maximum=TimeSeriesBoolean(
                values=model_result.rate_exceeds_maximum,
                periods=Periods([current_period]),
                unit=Unit.NONE,
            ),
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
                core_results.CompressorModelResult(
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
                    rate_sm3_day=model_result.rate_sm3_day,
                    stage_results=model_result.stage_results,
                    failure_status=model_result.failure_status,
                    inlet_stream_condition=model_result.inlet_stream_condition,
                    outlet_stream_condition=model_result.outlet_stream_condition,
                )
            ],
        )
