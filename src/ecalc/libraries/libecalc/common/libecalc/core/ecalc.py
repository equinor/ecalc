from typing import Dict

import libecalc.dto.components
import numpy as np
from libecalc import dto
from libecalc.common.list_utils import elementwise_sum
from libecalc.core.consumers.consumer_system import ConsumerSystem
from libecalc.core.consumers.direct_emitter import DirectEmitter
from libecalc.core.consumers.generator_set import Genset
from libecalc.core.consumers.legacy_consumer.component import Consumer
from libecalc.core.models.fuel import FuelModel
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.graph import Graph
from libecalc.dto.types import ConsumptionType


class EnergyCalculator:
    def __init__(
        self,
        graph: Graph,
    ):
        self._graph = graph

    def evaluate_energy_usage(self, variables_map: dto.VariablesMap) -> Dict[str, EcalcModelResult]:
        component_ids = list(reversed(self._graph.sorted_component_ids))
        component_dtos = [self._graph.get_component(component_id) for component_id in component_ids]

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
            elif isinstance(component_dto, libecalc.dto.components.PumpSystem):
                pump_system = ConsumerSystem(id=component_dto.id, consumers=component_dto.pumps)
                evaluated_operational_settings = component_dto.evaluate_operational_settings(
                    variables_map=variables_map,
                )
                consumer_results[component_dto.id] = pump_system.evaluate(
                    variables_map=variables_map, temporal_operational_settings=evaluated_operational_settings
                )
            elif isinstance(component_dto, libecalc.dto.components.CompressorSystem):
                compressor_system = ConsumerSystem(id=component_dto.id, consumers=component_dto.compressors)
                evaluated_operational_settings = component_dto.evaluate_operational_settings(
                    variables_map=variables_map,
                )
                system_result = compressor_system.evaluate(
                    variables_map=variables_map, temporal_operational_settings=evaluated_operational_settings
                )
                consumer_results[component_dto.id] = system_result
                for consumer_result in system_result.sub_components:
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
        for consumer_dto in self._graph.components.values():
            if isinstance(consumer_dto, (dto.FuelConsumer, dto.GeneratorSet)):
                fuel_model = FuelModel(consumer_dto.fuel)
                energy_usage = consumer_results[consumer_dto.id].component_result.energy_usage
                emission_results[consumer_dto.id] = fuel_model.evaluate_emissions(
                    variables_map=variables_map,
                    fuel_rate=np.asarray(energy_usage.values),
                )
            elif isinstance(consumer_dto, (dto.components.CompressorSystem, dto.components.PumpSystem)):
                if consumer_dto.consumes == ConsumptionType.FUEL:
                    fuel_model = FuelModel(consumer_dto.fuel)
                    energy_usage = consumer_results[consumer_dto.id].component_result.energy_usage
                    emission_results[consumer_dto.id] = fuel_model.evaluate_emissions(
                        variables_map=variables_map, fuel_rate=np.asarray(energy_usage.values)
                    )
            elif isinstance(consumer_dto, dto.DirectEmitter):
                emission_results[consumer_dto.id] = DirectEmitter(consumer_dto).evaluate(variables_map=variables_map)
        return emission_results
