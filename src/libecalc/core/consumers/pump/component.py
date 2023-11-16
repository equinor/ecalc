from __future__ import annotations

from typing import List, Optional

import numpy as np

from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.core.consumers.base import BaseConsumerWithoutOperationalSettings
from libecalc.core.models.pump import PumpModel
from libecalc.core.result import EcalcModelResult
from libecalc.core.result import results as core_results
from libecalc.domain.stream_conditions import Pressure, StreamConditions
from libecalc.dto.core_specs.pump.operational_settings import PumpOperationalSettings


class Pump(BaseConsumerWithoutOperationalSettings):
    def __init__(self, id: str, pump_model: PumpModel):
        self.id = id
        self._pump_model = pump_model
        self._operational_settings: Optional[PumpOperationalSettings] = None

    def get_max_rate(self, inlet_stream: StreamConditions, target_pressure: Pressure) -> List[float]:
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
        streams: List[StreamConditions],
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
        current_timestep = total_requested_inlet_stream.timestep

        outlet_stream.rate = total_requested_inlet_stream.rate

        component_result = core_results.PumpResult(
            id=self.id,
            timesteps=[current_timestep],
            power=TimeSeriesStreamDayRate(
                values=model_result.power,
                timesteps=[current_timestep],
                unit=model_result.power_unit,
            ).fill_nan(0.0),
            energy_usage=TimeSeriesStreamDayRate(
                values=model_result.energy_usage,
                timesteps=[current_timestep],
                unit=model_result.energy_usage_unit,
            ).fill_nan(0.0),
            inlet_liquid_rate_m3_per_day=TimeSeriesStreamDayRate(
                values=model_result.rate,
                timesteps=[current_timestep],
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
            inlet_pressure_bar=TimeSeriesFloat(
                values=model_result.suction_pressure,
                timesteps=[current_timestep],
                unit=Unit.BARA,
            ),
            outlet_pressure_bar=TimeSeriesFloat(
                values=model_result.discharge_pressure,
                timesteps=[current_timestep],
                unit=Unit.BARA,
            ),
            operational_head=TimeSeriesFloat(
                values=model_result.operational_head,
                timesteps=[current_timestep],
                unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
            ),
            is_valid=TimeSeriesBoolean(values=model_result.is_valid, timesteps=[current_timestep], unit=Unit.NONE),
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
                    timesteps=[current_timestep],
                    is_valid=TimeSeriesBoolean(
                        timesteps=[current_timestep],
                        values=model_result.is_valid,
                        unit=Unit.NONE,
                    ),
                    power=TimeSeriesStreamDayRate(
                        timesteps=[current_timestep],
                        values=model_result.power,
                        unit=model_result.power_unit,
                    )
                    if model_result.power is not None
                    else None,
                    energy_usage=TimeSeriesStreamDayRate(
                        timesteps=[current_timestep],
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
