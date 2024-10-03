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
from libecalc.core.models.pump import PumpModel, create_pump_model
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.results import PumpModelResult, PumpResult
from libecalc.domain.stream_conditions import StreamConditions
from libecalc.dto.component_graph import Component, ComponentID
from libecalc.dto.node_info import NodeInfo
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.yaml_types.components.yaml_pump import YamlPump


class Pump(Component, BaseConsumerWithoutOperationalSettings):
    def __init__(self, yaml_pump: YamlPump, reference_service: ReferenceService):
        self._yaml_pump = yaml_pump
        self.reference_service = reference_service

        self._ecalc_model_results: Dict[datetime, EcalcModelResult] = {}

    @property
    def id(self) -> ComponentID:
        return generate_id(self._yaml_pump.name)

    @property
    def name(self) -> str:
        return self._yaml_pump.name

    def get_node_info(self) -> NodeInfo:
        return NodeInfo(
            id=self.id,
            name=self.name,
            component_level=ComponentLevel.CONSUMER,
            component_type=ComponentType.PUMP_V2,
        )

    def get_ecalc_model_result(self) -> EcalcModelResult:
        first_result, *rest_results = list(self._ecalc_model_results.values())
        return first_result.merge(*rest_results)

    def _get_pump_model(self, timestep: datetime) -> PumpModel:
        model_reference_for_timestep = TemporalModel(
            define_time_model_for_period(self._yaml_pump.energy_usage_model, Period())
        ).get_model(timestep)
        return create_pump_model(self.reference_service.get_pump_model(model_reference_for_timestep))

    def get_max_rate(self, inlet_stream: StreamConditions, target_pressure: TimeSeriesFloat) -> List[float]:
        return (
            self._get_pump_model(inlet_stream.timestep)
            .get_max_standard_rate(
                suction_pressures=np.asarray([inlet_stream.pressure.value]),
                discharge_pressures=np.asarray([target_pressure.value]),
                fluid_density=np.asarray([inlet_stream.density.value]),
            )
            .tolist()[0]
        )

    def evaluate(self, streams: List[StreamConditions]) -> EcalcModelResult:
        timestep = streams[0].timestep
        inlet_streams = streams[:-1]
        outlet_stream = streams[-1]

        model_result = self._get_pump_model(timestep).evaluate_streams(
            inlet_streams=inlet_streams,
            outlet_stream=outlet_stream,
        )

        # Mixing all input rates to get total rate passed through compressor. Used when reporting streams.
        total_requested_inlet_stream = StreamConditions.mix_all(inlet_streams)
        total_requested_inlet_stream.name = "Total inlet"
        current_timestep = total_requested_inlet_stream.timestep

        outlet_stream.rate = total_requested_inlet_stream.rate

        component_result = PumpResult(
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
                PumpModelResult(
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
