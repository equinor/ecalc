from __future__ import annotations

from typing import List, Optional

import numpy as np

from libecalc.common.units import Unit
from libecalc.core.consumers.base import Consumer
from libecalc.core.consumers.compressor.result import CompressorResult
from libecalc.core.models.compressor import CompressorModel
from libecalc.domain.stream_conditions import Pressure, Rate, StreamConditions
from libecalc.dto.core_specs.compressor.operational_settings import (
    CompressorOperationalSettings,
)


class Compressor(Consumer):
    def __init__(self, id: str, compressor_model: CompressorModel):
        self.id = id
        self._compressor_model = compressor_model
        self._operational_settings: Optional[CompressorOperationalSettings] = None

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
        streams: List[StreamConditions],
    ) -> CompressorResult:
        inlet_streams = streams[:-1]
        outlet_stream = streams[-1]

        model_result = self._compressor_model.evaluate_streams(
            inlet_streams=inlet_streams,
            outlet_stream=outlet_stream,
        )

        # Mixing all input rates to get total rate passed through compressor. Used when reporting streams.
        total_requested_inlet_stream = StreamConditions.mix_all(inlet_streams)
        total_requested_inlet_stream.name = "Total inlet"
        current_timestep = total_requested_inlet_stream.timestep

        outlet_stream.rate = total_requested_inlet_stream.rate

        return CompressorResult(
            id=self.id,
            timestep=current_timestep,
            power=Rate(
                value=model_result.power[0],
                unit=model_result.power_unit,
            ),
            energy_usage=Rate(value=model_result.energy_usage[0], unit=model_result.energy_usage_unit),
            is_valid=model_result.is_valid[0],
            recirculation_loss=Rate(value=model_result.recirculation_loss[0], unit=Unit.MEGA_WATT),
            rate_exceeds_maximum=model_result.rate_exceeds_maximum[0],
            streams=[
                total_requested_inlet_stream,
                *inlet_streams,
                outlet_stream.copy(
                    {"pressure": Pressure(value=model_result.outlet_pressure_before_choking[0], unit=Unit.BARA)}
                ),
                outlet_stream,
            ],
        )
