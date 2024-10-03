from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.priorities import Priorities, PriorityID
from libecalc.common.priority_optimizer import ComponentID, PriorityOptimizer
from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.string.string_utils import generate_id, to_camel_case
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesInt, TimeSeriesStreamDayRate, TimeSeriesString
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.consumers.consumer_system import ConsumerSystem
from libecalc.core.result import ComponentResult, EcalcModelResult
from libecalc.dto.component_graph import Component, ProcessGraph
from libecalc.dto.node_info import NodeInfo
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.components.consumers.factory import create_consumer
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.yaml_types.components.system.yaml_consumer_system import YamlConsumerSystem


class EcalcBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class Crossover(EcalcBaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stream_name: Optional[str] = Field(None)
    from_component_id: str
    to_component_id: str


class SystemComponentConditions(EcalcBaseModel):
    crossover: List[Crossover]


class ConsumerSystemComponent(ProcessGraph, Component):
    def __init__(
        self,
        yaml_consumer_system: YamlConsumerSystem,
        reference_service: ReferenceService,
        target_period: Period,
        regularity: Dict[datetime, Expression],
        default_fuel_reference: Optional[str],
        expression_evaluator: ExpressionEvaluator,
    ):
        self._expression_evaluator = expression_evaluator
        self._yaml_consumer_system = yaml_consumer_system
        self._reference_service = reference_service

        self._consumers = [
            create_consumer(
                consumer=consumer,
                reference_service=reference_service,
            )
            for consumer in self._yaml_consumer_system.consumers
        ]
        self._consumer_name_to_id_map = {consumer.name: consumer.id for consumer in self._consumers}

        self._system_result: Optional[EcalcModelResult] = None

    @property
    def id(self):
        return generate_id()

    @property
    def name(self) -> str:
        return self._yaml_consumer_system.name

    def get_node_info(self) -> NodeInfo:
        return NodeInfo(
            id=self.id,
            name=self.name,
            component_level=ComponentLevel.SYSTEM,
            component_type=ComponentType.CONSUMER_SYSTEM_V2,
        )

    def get_components(self) -> List[Component]:
        return [self, *self._consumers]

    def get_ecalc_model_result(self) -> EcalcModelResult:
        return self._system_result

    def _evaluate_stream_conditions(
        self,
    ) -> Priorities[Dict[ComponentID, List[TimeSeriesStreamConditions]]]:
        parsed_priorities: Priorities[Dict[ComponentID, List[TimeSeriesStreamConditions]]] = defaultdict(dict)
        for priority_name, priority in self._yaml_consumer_system.stream_conditions_priorities.items():
            for consumer_name, streams_conditions in priority.items():
                parsed_priorities[priority_name][generate_id(consumer_name)] = [
                    TimeSeriesStreamConditions(
                        id=generate_id(consumer_name, stream_name),
                        name="-".join([consumer_name, stream_name]),
                        rate=TimeSeriesStreamDayRate(
                            timesteps=self._expression_evaluator.get_time_vector(),
                            values=self._expression_evaluator.evaluate(
                                convert_expression(stream_conditions.rate.value)
                            ).tolist(),
                            unit=stream_conditions.rate.unit,
                        )
                        if stream_conditions.rate is not None
                        else None,
                        pressure=TimeSeriesFloat(
                            timesteps=self._expression_evaluator.get_time_vector(),
                            values=self._expression_evaluator.evaluate(
                                convert_expression(stream_conditions.pressure.value)
                            ).tolist(),
                            unit=stream_conditions.pressure.unit,
                        )
                        if stream_conditions.pressure is not None
                        else None,
                        fluid_density=TimeSeriesFloat(
                            timesteps=self._expression_evaluator.get_time_vector(),
                            values=self._expression_evaluator.evaluate(
                                convert_expression(stream_conditions.fluid_density.value)
                            ).tolist(),
                            unit=stream_conditions.fluid_density.unit,
                        )
                        if stream_conditions.fluid_density is not None
                        else None,
                    )
                    for stream_name, stream_conditions in streams_conditions.items()
                ]
        return dict(parsed_priorities)

    def _get_system_conditions(self) -> SystemComponentConditions:
        if self._yaml_consumer_system.component_conditions is not None:
            return SystemComponentConditions(
                crossover=[
                    Crossover(
                        from_component_id=self._consumer_name_to_id_map[crossover_stream.from_],
                        to_component_id=self._consumer_name_to_id_map[crossover_stream.to],
                        stream_name=crossover_stream.name,
                    )
                    for crossover_stream in self._yaml_consumer_system.component_conditions.crossover
                ]
                if self._yaml_consumer_system.component_conditions.crossover is not None
                else [],
            )
        else:
            return SystemComponentConditions(
                crossover=[],
            )

    def evaluate(self, period: Period = None) -> None:
        evaluated_stream_conditions = self._evaluate_stream_conditions()
        optimizer = PriorityOptimizer()

        results_per_timestep: Dict[str, Dict[datetime, ComponentResult]] = defaultdict(dict)
        priorities_used = TimeSeriesString(
            timesteps=[],
            values=[],
            unit=Unit.NONE,
        )

        for timestep in self._expression_evaluator.get_time_vector():
            if timestep not in period:
                continue

            consumer_system = ConsumerSystem(
                id=self.id,
                consumers=self._consumers,
                component_conditions=self._get_system_conditions(),
            )

            def evaluator(priority: PriorityID):
                stream_conditions_for_priority = evaluated_stream_conditions[priority]
                stream_conditions_for_timestep = {
                    component_id: [stream_condition.for_timestep(timestep) for stream_condition in stream_conditions]
                    for component_id, stream_conditions in stream_conditions_for_priority.items()
                }
                return consumer_system.evaluate_consumers(stream_conditions_for_timestep)

            optimizer_result = optimizer.optimize(
                priorities=list(evaluated_stream_conditions.keys()),
                evaluator=evaluator,
            )
            priorities_used.append(timestep=timestep, value=optimizer_result.priority_used)
            for consumer_result in optimizer_result.priority_results:
                results_per_timestep[consumer_result.id][timestep] = consumer_result

        # Convert to legacy compatible operational_settings_used
        priorities_to_int_map = {
            priority_name: index + 1 for index, priority_name in enumerate(evaluated_stream_conditions.keys())
        }
        operational_settings_used = TimeSeriesInt(
            timesteps=priorities_used.timesteps,
            values=[priorities_to_int_map[priority_name] for priority_name in priorities_used.values],
            unit=priorities_used.unit,
        )

        system_result = ConsumerSystem.get_system_result(
            id=self.id,
            consumer_results=[consumer.get_ecalc_model_result() for consumer in self._consumers],
            operational_settings_used=operational_settings_used,
        )
        self._system_result = system_result
