from typing import Dict

from libecalc.common.math.numbers import Numbers
from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.component_graph import (
    Component,
    ComponentGraph,
    Emitter,
    FuelConsumer,
    PowerConsumer,
    PowerProvider,
    ProcessGraph,
)


class EnergyCalculator:
    def __init__(
        self,
        graph: ComponentGraph,
    ):
        self._graph = graph

    def evaluate_energy_usage(self) -> Dict[str, EcalcModelResult]:
        component_ids = list(reversed(self._graph.sorted_node_ids))
        components_to_evaluate = [self._graph.get_node(component_id) for component_id in component_ids]

        consumer_results: Dict[str, EcalcModelResult] = {}
        power_requirements: Dict[str, TimeSeriesStreamDayRate] = {}

        for component in components_to_evaluate:
            if isinstance(component, PowerConsumer):
                power_requirements[component.id] = component.get_power_requirement()

            elif isinstance(component, PowerProvider):
                power_consumers_for_provider = self._graph.get_successors(component.id)
                power_requirements_for_provider = [
                    power_requirements[power_consumer_id] for power_consumer_id in power_consumers_for_provider
                ]
                component.provide_power(power_requirements_for_provider)

            elif isinstance(component, FuelConsumer):
                component.get_fuel_usage()

            elif isinstance(component, ProcessGraph):
                component.evaluate()

        for component in components_to_evaluate:
            if isinstance(component, ProcessGraph):
                for sub_component in component.get_components():
                    consumer_results[sub_component.id] = sub_component.get_ecalc_model_result()
            elif isinstance(component, Component):
                consumer_results[component.id] = component.get_ecalc_model_result()

        return Numbers.format_results_to_precision(consumer_results, precision=6)

    def evaluate_emissions(
        self,
    ) -> Dict[str, Dict[str, EmissionResult]]:
        """
        Calculate emissions for fuel consumers and emitters

        Returns: a mapping from consumer_id to emissions
        """
        emission_results: Dict[str, Dict[str, EmissionResult]] = {}
        for consumer_dto in self._graph.nodes.values():
            if isinstance(consumer_dto, Emitter):
                emission_results[consumer_dto.id] = consumer_dto.get_emissions()

            elif isinstance(consumer_dto, ProcessGraph):
                for sub_component in consumer_dto.get_components():
                    if isinstance(sub_component, Emitter):
                        emission_results[sub_component.id] = sub_component.get_emissions()

        return Numbers.format_results_to_precision(emission_results, precision=6)
