from datetime import datetime
from typing import Dict, List

import numpy as np

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesBoolean, TimeSeriesFloat, TimeSeriesStreamDayRate
from libecalc.core.consumers.base import BaseConsumerWithoutOperationalSettings
from libecalc.core.models.compressor import CompressorModel, create_compressor_model
from libecalc.core.result import CompressorModelResult, CompressorResult, EcalcModelResult
from libecalc.domain.stream_conditions import StreamConditions
from libecalc.dto.component_graph import Component, ComponentID
from libecalc.dto.node_info import NodeInfo
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.yaml_types.components.yaml_compressor import YamlCompressor


class Compressor(Component, BaseConsumerWithoutOperationalSettings):
    def __init__(self, yaml_compressor: YamlCompressor, reference_service: ReferenceService):
        self._yaml_compressor = yaml_compressor
        self.reference_service = reference_service

        self._ecalc_model_results: Dict[datetime, EcalcModelResult] = {}

    @property
    def id(self) -> ComponentID:
        return generate_id(self._yaml_compressor.name)

    @property
    def name(self) -> str:
        return self._yaml_compressor.name

    def get_node_info(self) -> NodeInfo:
        return NodeInfo(
            id=self.id,
            name=self.name,
            component_level=ComponentLevel.CONSUMER,
            component_type=ComponentType.COMPRESSOR_V2,
        )

    def get_ecalc_model_result(self) -> EcalcModelResult:
        first_result, *rest_results = list(self._ecalc_model_results.values())
        return first_result.merge(*rest_results)

    def _get_compressor_model(self, timestep: datetime) -> CompressorModel:
        model_reference_for_timestep = TemporalModel(
            define_time_model_for_period(self._yaml_compressor.energy_usage_model, Period())
        ).get_model(timestep)
        return create_compressor_model(self.reference_service.get_compressor_model(model_reference_for_timestep))

    def get_max_rate(self, inlet_stream: StreamConditions, target_pressure: TimeSeriesFloat) -> List[float]:
        compressor_model = self._get_compressor_model(inlet_stream.timestep)
        return compressor_model.get_max_standard_rate(
            suction_pressures=np.asarray([inlet_stream.pressure.value]),
            discharge_pressures=np.asarray([target_pressure.value]),
        ).tolist()[0]

    def evaluate(self, streams: List[StreamConditions]) -> EcalcModelResult:
        timestep = streams[0].timestep
        compressor_model = self._get_compressor_model(timestep)
        inlet_streams = streams[:-1]
        outlet_stream = streams[-1]

        model_result = compressor_model.evaluate_streams(
            inlet_streams=inlet_streams,
            outlet_stream=outlet_stream,
        )

        # Mixing all input rates to get total rate passed through compressor. Used when reporting streams.
        total_requested_inlet_stream = StreamConditions.mix_all(inlet_streams)
        total_requested_inlet_stream.name = "Total inlet"
        current_timestep = total_requested_inlet_stream.timestep

        outlet_stream.rate = total_requested_inlet_stream.rate

        energy_usage = TimeSeriesStreamDayRate(
            values=model_result.energy_usage,
            timesteps=[current_timestep],
            unit=model_result.energy_usage_unit,
        )

        component_result = CompressorResult(
            timesteps=[current_timestep],
            power=TimeSeriesStreamDayRate(
                values=model_result.power,
                timesteps=[current_timestep],
                unit=model_result.power_unit,
            ).fill_nan(0.0),
            energy_usage=energy_usage.fill_nan(0.0),
            is_valid=TimeSeriesBoolean(values=model_result.is_valid, timesteps=[current_timestep], unit=Unit.NONE),
            id=self.id,
            recirculation_loss=TimeSeriesStreamDayRate(
                values=model_result.recirculation_loss,
                timesteps=[current_timestep],
                unit=Unit.MEGA_WATT,
            ),
            rate_exceeds_maximum=TimeSeriesBoolean(
                values=model_result.rate_exceeds_maximum,
                timesteps=[current_timestep],
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

        ecalc_model_result = EcalcModelResult(
            component_result=component_result,
            sub_components=[],
            models=[
                CompressorModelResult(
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
                    rate_sm3_day=model_result.rate_sm3_day,
                    stage_results=model_result.stage_results,
                    failure_status=model_result.failure_status,
                    inlet_stream_condition=model_result.inlet_stream_condition,
                    outlet_stream_condition=model_result.outlet_stream_condition,
                )
            ],
        )
        self._ecalc_model_results[timestep] = ecalc_model_result
        return ecalc_model_result
