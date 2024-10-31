from collections import defaultdict

import numpy as np

import libecalc.dto.components
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.list.list_utils import elementwise_sum
from libecalc.common.math.numbers import Numbers
from libecalc.common.priorities import PriorityID
from libecalc.common.priority_optimizer import PriorityOptimizer
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesInt, TimeSeriesString
from libecalc.common.variables import VariablesMap
from libecalc.core.consumers.consumer_system import ConsumerSystem
from libecalc.core.consumers.factory import create_consumer
from libecalc.core.consumers.generator_set import Genset
from libecalc.core.consumers.legacy_consumer.component import Consumer
from libecalc.core.consumers.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.core.models.fuel import FuelModel
from libecalc.core.models.generator import GeneratorModelSampled
from libecalc.core.result import ComponentResult, EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.components import (
    ConsumerSystem as ConsumerSystemDTO,
)
from libecalc.dto.components import (
    ElectricityConsumer as ElectricityConsumerDTO,
)
from libecalc.dto.components import (
    FuelConsumer as FuelConsumerDTO,
)
from libecalc.dto.components import (
    GeneratorSet as GeneratorSetDTO,
)
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlDirectTypeEmitter,
    YamlOilTypeEmitter,
)


class EnergyCalculator:
    def __init__(
        self,
        graph: ComponentGraph,
    ):
        self._graph = graph

    def evaluate_energy_usage(self, variables_map: VariablesMap) -> dict[str, EcalcModelResult]:
        component_ids = list(reversed(self._graph.sorted_node_ids))
        component_dtos = [self._graph.get_node(component_id) for component_id in component_ids]

        consumer_results: dict[str, EcalcModelResult] = {}

        for component_dto in component_dtos:
            if isinstance(component_dto, ElectricityConsumerDTO | FuelConsumerDTO):
                consumer = Consumer(
                    id=component_dto.id,
                    name=component_dto.name,
                    component_type=component_dto.component_type,
                    regularity=TemporalModel(component_dto.regularity),
                    consumes=component_dto.consumes,
                    energy_usage_model=TemporalModel(
                        {
                            period: EnergyModelMapper.from_dto_to_domain(model)
                            for period, model in component_dto.energy_usage_model.items()
                        }
                    ),
                )
                consumer_results[component_dto.id] = consumer.evaluate(expression_evaluator=variables_map)
            elif isinstance(component_dto, GeneratorSetDTO):
                fuel_consumer = Genset(
                    id=component_dto.id,
                    name=component_dto.name,
                    temporal_generator_set_model=TemporalModel(
                        {
                            period: GeneratorModelSampled(
                                fuel_values=model.fuel_values,
                                power_values=model.power_values,
                                energy_usage_adjustment_constant=model.energy_usage_adjustment_constant,
                                energy_usage_adjustment_factor=model.energy_usage_adjustment_factor,
                            )
                            for period, model in component_dto.generator_set_model.items()
                        }
                    ),
                )

                power_requirement = elementwise_sum(
                    *[
                        consumer_results[consumer_id].component_result.power.values
                        for consumer_id in self._graph.get_successors(component_dto.id)
                    ],
                    periods=variables_map.periods,
                )

                consumer_results[component_dto.id] = EcalcModelResult(
                    component_result=fuel_consumer.evaluate(
                        expression_evaluator=variables_map,
                        power_requirement=power_requirement,
                    ),
                    models=[],
                    sub_components=[],
                )
            elif isinstance(component_dto, libecalc.dto.components.ConsumerSystem):
                evaluated_stream_conditions = component_dto.evaluate_stream_conditions(
                    expression_evaluator=variables_map,
                )
                optimizer = PriorityOptimizer()

                results_per_period: dict[str, dict[Period, ComponentResult]] = defaultdict(dict)
                priorities_used = []
                for period in variables_map.periods:
                    consumers_for_period = [
                        create_consumer(
                            consumer=consumer,
                            period=period,
                        )
                        for consumer in component_dto.consumers
                    ]

                    consumer_system = ConsumerSystem(
                        id=component_dto.id,
                        consumers=consumers_for_period,
                        component_conditions=component_dto.component_conditions,
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
                    periods=variables_map.periods,
                    values=priorities_used,
                    unit=Unit.NONE,
                )
                # merge consumer results
                consumer_ids = [consumer.id for consumer in component_dto.consumers]
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
                    id=component_dto.id,
                    consumer_results=merged_consumer_results,
                    operational_settings_used=operational_settings_used,
                )
                consumer_results[component_dto.id] = system_result
                for consumer_result in merged_consumer_results:
                    consumer_results[consumer_result.id] = EcalcModelResult(
                        component_result=consumer_result,
                        sub_components=[],
                        models=[],
                    )

        return Numbers.format_results_to_precision(consumer_results, precision=6)

    def evaluate_emissions(
        self, variables_map: VariablesMap, consumer_results: dict[str, EcalcModelResult]
    ) -> dict[str, dict[str, EmissionResult]]:
        """
        Calculate emissions for fuel consumers and emitters

        Args:
            variables_map:
            consumer_results:

        Returns: a mapping from consumer_id to emissions
        """
        emission_results: dict[str, dict[str, EmissionResult]] = {}
        for consumer_dto in self._graph.nodes.values():
            if isinstance(consumer_dto, FuelConsumerDTO | GeneratorSetDTO):
                fuel_model = FuelModel(consumer_dto.fuel)
                energy_usage = consumer_results[consumer_dto.id].component_result.energy_usage
                emission_results[consumer_dto.id] = fuel_model.evaluate_emissions(
                    expression_evaluator=variables_map,
                    fuel_rate=np.asarray(energy_usage.values),
                )
            elif isinstance(consumer_dto, ConsumerSystemDTO):
                if consumer_dto.consumes == ConsumptionType.FUEL:
                    fuel_model = FuelModel(consumer_dto.fuel)
                    energy_usage = consumer_results[consumer_dto.id].component_result.energy_usage
                    emission_results[consumer_dto.id] = fuel_model.evaluate_emissions(
                        expression_evaluator=variables_map, fuel_rate=np.asarray(energy_usage.values)
                    )
            elif isinstance(consumer_dto, YamlDirectTypeEmitter | YamlOilTypeEmitter):
                installation_id = self._graph.get_parent_installation_id(consumer_dto.id)
                installation = self._graph.get_node(installation_id)

                venting_emitter_results = {}
                emission_rates = consumer_dto.get_emissions(
                    expression_evaluator=variables_map, regularity=installation.regularity
                )

                for emission_name, emission_rate in emission_rates.items():
                    emission_result = EmissionResult(
                        name=emission_name,
                        periods=variables_map.get_periods(),
                        rate=emission_rate,
                    )
                    venting_emitter_results[emission_name] = emission_result
                emission_results[consumer_dto.id] = venting_emitter_results
        return Numbers.format_results_to_precision(emission_results, precision=6)
