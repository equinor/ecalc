import operator
from collections import defaultdict
from functools import reduce
from typing import Optional

import libecalc.dto.components
from libecalc.application.energy.component_energy_context import ComponentEnergyContext
from libecalc.application.energy.emitter import Emitter
from libecalc.application.energy.energy_model import EnergyModel
from libecalc.common.math.numbers import Numbers
from libecalc.common.priorities import PriorityID
from libecalc.common.priority_optimizer import PriorityOptimizer
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesInt, TimeSeriesStreamDayRate, TimeSeriesString
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.consumers.consumer_system import ConsumerSystem
from libecalc.core.consumers.factory import create_consumer
from libecalc.core.consumers.generator_set import Genset
from libecalc.core.consumers.legacy_consumer.component import Consumer
from libecalc.core.consumers.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.core.models.generator import GeneratorModelSampled
from libecalc.core.result import ComponentResult, EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.components import (
    ElectricityConsumer as ElectricityConsumerDTO,
)
from libecalc.dto.components import (
    FuelConsumer as FuelConsumerDTO,
)
from libecalc.dto.components import (
    GeneratorSet as GeneratorSetDTO,
)


class Context(ComponentEnergyContext):
    def __init__(
        self,
        energy_model: EnergyModel,
        consumer_results: dict[str, EcalcModelResult],
        component_id: str,
    ):
        self._energy_model = energy_model
        self._consumer_results = consumer_results
        self._component_id = component_id

    def get_power_requirement(self) -> Optional[TimeSeriesFloat]:
        consumer_power_usage = [
            self._consumer_results[consumer.id].component_result.power
            for consumer in self._energy_model.get_consumers(self._component_id)
            if self._consumer_results[consumer.id].component_result.power is not None
        ]

        if len(consumer_power_usage) < 1:
            return None

        if len(consumer_power_usage) == 1:
            return consumer_power_usage[0]

        return reduce(operator.add, consumer_power_usage)

    def get_fuel_usage(self) -> Optional[TimeSeriesStreamDayRate]:
        energy_usage = self._consumer_results[self._component_id].component_result.energy_usage
        if energy_usage.unit == Unit.MEGA_WATT:
            # energy usage is power usage, not fuel usage.
            return None
        return energy_usage


class EnergyCalculator:
    def __init__(
        self,
        energy_model: EnergyModel,
        expression_evaluator: ExpressionEvaluator,
    ):
        self._energy_model = energy_model
        self._expression_evaluator = expression_evaluator
        self._consumer_results: dict[str, EcalcModelResult] = {}

    def _get_context(self, component_id: str) -> ComponentEnergyContext:
        return Context(
            energy_model=self._energy_model,
            consumer_results=self._consumer_results,
            component_id=component_id,
        )

    def evaluate_energy_usage(self) -> dict[str, EcalcModelResult]:
        energy_components = self._energy_model.get_energy_components()

        for energy_component in energy_components:
            if isinstance(energy_component, ElectricityConsumerDTO | FuelConsumerDTO):
                consumer = Consumer(
                    id=energy_component.id,
                    name=energy_component.name,
                    component_type=energy_component.component_type,
                    regularity=TemporalModel(energy_component.regularity),
                    consumes=energy_component.consumes,
                    energy_usage_model=TemporalModel(
                        {
                            period: EnergyModelMapper.from_dto_to_domain(model)
                            for period, model in energy_component.energy_usage_model.items()
                        }
                    ),
                )
                self._consumer_results[energy_component.id] = consumer.evaluate(
                    expression_evaluator=self._expression_evaluator
                )
            elif isinstance(energy_component, GeneratorSetDTO):
                fuel_consumer = Genset(
                    id=energy_component.id,
                    name=energy_component.name,
                    temporal_generator_set_model=TemporalModel(
                        {
                            period: GeneratorModelSampled(
                                fuel_values=model.fuel_values,
                                power_values=model.power_values,
                                energy_usage_adjustment_constant=model.energy_usage_adjustment_constant,
                                energy_usage_adjustment_factor=model.energy_usage_adjustment_factor,
                            )
                            for period, model in energy_component.generator_set_model.items()
                        }
                    ),
                )

                context = self._get_context(energy_component.id)

                self._consumer_results[energy_component.id] = EcalcModelResult(
                    component_result=fuel_consumer.evaluate(
                        expression_evaluator=self._expression_evaluator,
                        power_requirement=context.get_power_requirement(),
                    ),
                    models=[],
                    sub_components=[],
                )
            elif isinstance(energy_component, libecalc.dto.components.ConsumerSystem):
                evaluated_stream_conditions = energy_component.evaluate_stream_conditions(
                    expression_evaluator=self._expression_evaluator,
                )
                optimizer = PriorityOptimizer()

                results_per_period: dict[str, dict[Period, ComponentResult]] = defaultdict(dict)
                priorities_used = []
                for period in self._expression_evaluator.get_periods():
                    consumers_for_period = [
                        create_consumer(
                            consumer=consumer,
                            period=period,
                        )
                        for consumer in energy_component.consumers
                    ]

                    consumer_system = ConsumerSystem(
                        id=energy_component.id,
                        consumers=consumers_for_period,
                        component_conditions=energy_component.component_conditions,
                    )

                    def evaluator(priority: PriorityID):
                        stream_conditions_for_priority = evaluated_stream_conditions[priority]
                        stream_conditions_for_timestep = {
                            component_id: [
                                stream_condition.for_period(period) for stream_condition in stream_conditions
                            ]
                            for component_id, stream_conditions in stream_conditions_for_priority.items()
                        }
                        return consumer_system.evaluate_consumers(stream_conditions_for_timestep)

                    optimizer_result = optimizer.optimize(
                        priorities=list(evaluated_stream_conditions.keys()),
                        evaluator=evaluator,
                    )
                    priorities_used.append(optimizer_result.priority_used)
                    for consumer_result in optimizer_result.priority_results:
                        results_per_period[consumer_result.id][period] = consumer_result

                priorities_used = TimeSeriesString(
                    periods=self._expression_evaluator.get_periods(),
                    values=priorities_used,
                    unit=Unit.NONE,
                )
                # merge consumer results
                consumer_ids = [consumer.id for consumer in energy_component.consumers]
                merged_consumer_results = []
                for consumer_id in consumer_ids:
                    first_result, *rest_results = list(results_per_period[consumer_id].values())
                    merged_consumer_results.append(first_result.merge(*rest_results))

                # Convert to legacy compatible operational_settings_used
                priorities_to_int_map = {
                    priority_name: index + 1 for index, priority_name in enumerate(evaluated_stream_conditions.keys())
                }
                operational_settings_used = TimeSeriesInt(
                    periods=priorities_used.periods,
                    values=[priorities_to_int_map[priority_name] for priority_name in priorities_used.values],
                    unit=priorities_used.unit,
                )

                system_result = ConsumerSystem.get_system_result(
                    id=energy_component.id,
                    consumer_results=merged_consumer_results,
                    operational_settings_used=operational_settings_used,
                )
                self._consumer_results[energy_component.id] = system_result
                for consumer_result in merged_consumer_results:
                    self._consumer_results[consumer_result.id] = EcalcModelResult(
                        component_result=consumer_result,
                        sub_components=[],
                        models=[],
                    )

        self._consumer_results = Numbers.format_results_to_precision(self._consumer_results, precision=6)
        return self._consumer_results

    def evaluate_emissions(self) -> dict[str, dict[str, EmissionResult]]:
        """
        Calculate emissions for fuel consumers and emitters

        Returns: a mapping from consumer_id to emissions
        """
        emission_results: dict[str, dict[str, EmissionResult]] = {}
        for energy_component in self._energy_model.get_energy_components():
            if isinstance(energy_component, Emitter):
                emission_result = energy_component.evaluate_emissions(
                    energy_context=self._get_context(energy_component.id),
                    energy_model=self._energy_model,
                    expression_evaluator=self._expression_evaluator,
                )

                if emission_result is not None:
                    emission_results[energy_component.id] = emission_result

        return Numbers.format_results_to_precision(emission_results, precision=6)
