from collections import defaultdict
from datetime import datetime
from functools import reduce
from typing import Dict

import numpy as np

import libecalc.dto.components
from libecalc import dto
from libecalc.common.list.list_utils import elementwise_sum
from libecalc.common.priorities import PriorityID
from libecalc.common.priority_optimizer import PriorityOptimizer
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesInt, TimeSeriesString
from libecalc.core.consumers.consumer_system import ConsumerSystem
from libecalc.core.consumers.factory import create_consumer
from libecalc.core.consumers.generator_set import Genset
from libecalc.core.consumers.legacy_consumer.component import Consumer
from libecalc.core.models.fuel import FuelModel
from libecalc.core.result import ComponentResult, EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.types import ConsumptionType
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)


def merge_results(results_per_timestep: Dict[datetime, EcalcModelResult]) -> EcalcModelResult:
    return reduce(lambda acc, x: acc.merge(x), results_per_timestep.values())


class EnergyCalculator:
    def __init__(
        self,
        graph: ComponentGraph,
    ):
        self._graph = graph

    def evaluate_energy_usage(self, variables_map: dto.VariablesMap) -> Dict[str, EcalcModelResult]:
        component_ids = list(reversed(self._graph.sorted_node_ids))
        component_dtos = [self._graph.get_node(component_id) for component_id in component_ids]

        consumer_results: Dict[str, EcalcModelResult] = {}

        for component_dto in component_dtos:
            if isinstance(component_dto, (dto.ElectricityConsumer, dto.FuelConsumer)):
                consumer = Consumer(consumer_dto=component_dto)
                consumer_results[component_dto.id] = consumer.evaluate(variables_map=variables_map)
            elif isinstance(component_dto, dto.GeneratorSet):
                fuel_consumer = Genset(component_dto)

                power_requirement = elementwise_sum(
                    *[
                        consumer_results[consumer_id].component_result.power.values
                        for consumer_id in self._graph.get_successors(component_dto.id)
                    ],
                    timesteps=variables_map.time_vector,
                )

                consumer_results[component_dto.id] = EcalcModelResult(
                    component_result=fuel_consumer.evaluate(
                        variables_map=variables_map,
                        power_requirement=power_requirement,
                    ),
                    models=[],
                    sub_components=[],
                )
            elif isinstance(component_dto, libecalc.dto.components.ConsumerSystem):
                evaluated_stream_conditions = component_dto.evaluate_stream_conditions(
                    variables_map=variables_map,
                )
                optimizer = PriorityOptimizer()

                results_per_timestep: Dict[str, Dict[datetime, ComponentResult]] = defaultdict(dict)
                priorities_used = TimeSeriesString(
                    timesteps=[],
                    values=[],
                    unit=Unit.NONE,
                )
                for timestep in variables_map.time_vector:
                    consumers_for_timestep = [
                        create_consumer(
                            consumer=consumer,
                            timestep=timestep,
                        )
                        for consumer in component_dto.consumers
                    ]

                    consumer_system = ConsumerSystem(
                        id=component_dto.id,
                        consumers=consumers_for_timestep,
                        component_conditions=component_dto.component_conditions,
                    )

                    def evaluator(priority: PriorityID):
                        stream_conditions_for_priority = evaluated_stream_conditions[priority]
                        stream_conditions_for_timestep = {
                            component_id: [
                                stream_condition.for_timestep(timestep) for stream_condition in stream_conditions
                            ]
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

                # merge consumer results
                consumer_ids = [consumer.id for consumer in component_dto.consumers]
                merged_consumer_results = []
                for consumer_id in consumer_ids:
                    first_result, *rest_results = list(results_per_timestep[consumer_id].values())
                    merged_consumer_results.append(first_result.merge(*rest_results))

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

        return consumer_results

    def evaluate_emissions(
        self, variables_map: dto.VariablesMap, consumer_results: Dict[str, EcalcModelResult]
    ) -> Dict[str, Dict[str, EmissionResult]]:
        """
        Calculate emissions for fuel consumers and emitters

        Args:
            variables_map:
            consumer_results:

        Returns: a mapping from consumer_id to emissions
        """
        emission_results: Dict[str, Dict[str, EmissionResult]] = {}
        for consumer_dto in self._graph.nodes.values():
            if isinstance(consumer_dto, (dto.FuelConsumer, dto.GeneratorSet)):
                fuel_model = FuelModel(consumer_dto.fuel)
                energy_usage = consumer_results[consumer_dto.id].component_result.energy_usage
                emission_results[consumer_dto.id] = fuel_model.evaluate_emissions(
                    variables_map=variables_map,
                    fuel_rate=np.asarray(energy_usage.values),
                )
            elif isinstance(consumer_dto, dto.components.ConsumerSystem):
                if consumer_dto.consumes == ConsumptionType.FUEL:
                    fuel_model = FuelModel(consumer_dto.fuel)
                    energy_usage = consumer_results[consumer_dto.id].component_result.energy_usage
                    emission_results[consumer_dto.id] = fuel_model.evaluate_emissions(
                        variables_map=variables_map, fuel_rate=np.asarray(energy_usage.values)
                    )
            elif isinstance(consumer_dto, YamlVentingEmitter):
                installation_id = self._graph.get_parent_installation_id(consumer_dto.id)
                installation = self._graph.get_node(installation_id)

                emission_rate = consumer_dto.get_emission_rate(
                    variables_map=variables_map, regularity=installation.regularity
                )

                emission_result = {
                    consumer_dto.emission.name: EmissionResult(
                        name=consumer_dto.name,
                        timesteps=variables_map.time_vector,
                        rate=emission_rate,
                    )
                }
                emission_results[consumer_dto.id] = emission_result
        return emission_results
