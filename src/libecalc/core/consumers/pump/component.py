from __future__ import annotations

from typing import List, Optional

import numpy as np

from libecalc.core.consumers.base import Consumer
from libecalc.core.consumers.pump.result import PumpResult
from libecalc.core.models.pump import PumpModel
from libecalc.domain.stream_conditions import Pressure, Rate, StreamConditions
from libecalc.dto.core_specs.pump.operational_settings import PumpOperationalSettings


class Pump(Consumer):
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
    ) -> PumpResult:
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

        return PumpResult(
            id=self.id,
            timestep=current_timestep,
            power=Rate(
                value=model_result.power[0],
                unit=model_result.power_unit,
            ),
            energy_usage=Rate(value=model_result.energy_usage[0], unit=model_result.energy_usage_unit),
            is_valid=model_result.is_valid[0],
            operational_head=model_result.operational_head[0],
            streams=[
                total_requested_inlet_stream,
                *inlet_streams,
                outlet_stream,
            ],
        )
