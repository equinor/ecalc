from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from libecalc import dto
from libecalc.common.stream import Stage, Stream
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.core.consumers.base import BaseConsumerWithoutOperationalSettings
from libecalc.core.models.pump import create_pump_model
from libecalc.core.models.results import PumpModelResult
from libecalc.core.result import EcalcModelResult
from libecalc.core.result import results as core_results
from libecalc.dto.core_specs.pump.operational_settings import PumpOperationalSettings


class Pump(BaseConsumerWithoutOperationalSettings):
    def __init__(self, id: str, energy_usage_model: Dict[datetime, dto.PumpModel]):
        self.id = id
        self._temporal_model = TemporalModel(
            data={timestep: create_pump_model(model) for timestep, model in energy_usage_model.items()}
        )

        self._operational_settings: Optional[PumpOperationalSettings] = None

    def get_max_rate(self, inlet_stream: Stream, target_pressure: TimeSeriesFloat) -> List[float]:
        """
        For each timestep, get the maximum rate that this pump can handle, given
        the operational settings given, such as in -and outlet pressures and fluid density (current conditions)

        Args:
            inlet_stream: the inlet stream
            target_pressure: the target pressure
        """
        results = []
        for timestep in inlet_stream.pressure.timesteps:
            pump = self._temporal_model.get_model(timestep)
            results.extend(
                pump.get_max_standard_rate(
                    suction_pressures=np.asarray(inlet_stream.pressure.values),
                    discharge_pressures=np.asarray(target_pressure.values),
                    fluid_density=np.asarray(inlet_stream.fluid_density.values),
                ).tolist()
            )
        return results

    def evaluate(
        self,
        streams: List[Stream],
    ) -> EcalcModelResult:
        model_results = []
        evaluated_timesteps = []

        timesteps = streams[0].rate.timesteps  # TODO: which timesteps should we useeeee
        inlet_streams = streams[:-1]
        outlet_stream = streams[-1]

        for timestep in timesteps:
            pump = self._temporal_model.get_model(timestep)
            stream_conditions_for_timestep = [
                stream_condition.get_subset_for_timestep(timestep) for stream_condition in streams
            ]
            inlet_streams_for_timestep = streams[:-1]
            outlet_stream_for_timestep = streams[-1]
            model_result = pump.evaluate_streams(
                inlet_streams=inlet_streams_for_timestep,
                outlet_stream=outlet_stream_for_timestep,
            )
            evaluated_timesteps.extend(stream_conditions_for_timestep[0].rate.timesteps)
            model_results.append(model_result)

        aggregated_result: Optional[PumpModelResult] = None
        for model_result in model_results:
            if aggregated_result is None:
                aggregated_result = model_result
            else:
                aggregated_result.extend(model_result)

        # Mixing all input rates to get total rate passed through compressor. Used when reporting streams.
        total_requested_inlet_stream = Stream.mix_all(inlet_streams)

        component_result = core_results.PumpResult(
            timesteps=evaluated_timesteps,
            power=TimeSeriesStreamDayRate(
                values=aggregated_result.power,
                timesteps=evaluated_timesteps,
                unit=aggregated_result.power_unit,
            ).fill_nan(0.0),
            energy_usage=TimeSeriesStreamDayRate(
                values=aggregated_result.energy_usage,
                timesteps=evaluated_timesteps,
                unit=aggregated_result.energy_usage_unit,
            ).fill_nan(0.0),
            inlet_liquid_rate_m3_per_day=TimeSeriesStreamDayRate(
                values=aggregated_result.rate,
                timesteps=evaluated_timesteps,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
            inlet_pressure_bar=TimeSeriesFloat(
                values=aggregated_result.suction_pressure,
                timesteps=evaluated_timesteps,
                unit=Unit.BARA,
            ),
            outlet_pressure_bar=TimeSeriesFloat(
                values=aggregated_result.discharge_pressure,
                timesteps=evaluated_timesteps,
                unit=Unit.BARA,
            ),
            operational_head=TimeSeriesFloat(
                values=aggregated_result.operational_head,
                timesteps=evaluated_timesteps,
                unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
            ),
            is_valid=TimeSeriesBoolean(
                values=aggregated_result.is_valid, timesteps=evaluated_timesteps, unit=Unit.NONE
            ),
            id=self.id,
            stages=[
                Stage(
                    name="inlet",
                    stream=total_requested_inlet_stream,
                ),
                Stage(
                    name="outlet",
                    stream=Stream(
                        name="outlet",
                        rate=total_requested_inlet_stream.rate,  # Actual, not requested, different because of crossover
                        pressure=outlet_stream.pressure,
                        fluid_density=total_requested_inlet_stream.fluid_density,
                    ),
                ),
            ],
        )

        return EcalcModelResult(
            component_result=component_result,
            sub_components=[],
            models=[
                core_results.PumpModelResult(
                    name="N/A",  # No context available to populate model name
                    timesteps=evaluated_timesteps,
                    is_valid=TimeSeriesBoolean(
                        timesteps=evaluated_timesteps,
                        values=aggregated_result.is_valid,
                        unit=Unit.NONE,
                    ),
                    power=TimeSeriesStreamDayRate(
                        timesteps=evaluated_timesteps,
                        values=aggregated_result.power,
                        unit=aggregated_result.power_unit,
                    )
                    if aggregated_result.power is not None
                    else None,
                    energy_usage=TimeSeriesStreamDayRate(
                        timesteps=evaluated_timesteps,
                        values=aggregated_result.energy_usage,
                        unit=aggregated_result.energy_usage_unit,
                    ),
                    inlet_liquid_rate_m3_per_day=aggregated_result.rate,
                    inlet_pressure_bar=aggregated_result.suction_pressure,
                    outlet_pressure_bar=aggregated_result.discharge_pressure,
                    operational_head=aggregated_result.operational_head,
                )
            ],
        )
