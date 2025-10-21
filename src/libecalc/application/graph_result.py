from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.common.variables import VariablesMap
from libecalc.core.result import ComponentResult
from libecalc.dto.component_graph import ComponentGraph


class GraphResult:
    def __init__(
        self,
        graph: ComponentGraph,
        consumer_results: dict[str, ComponentResult],
        emission_results: dict[str, dict[str, TimeSeriesStreamDayRate]],
        variables_map: VariablesMap,
    ):
        self.graph = graph
        self.consumer_results = consumer_results
        self.emission_results = emission_results
        self.variables_map = variables_map

    def get_installation(self, node_id: str) -> "GraphResult":
        subgraph = self.graph.get_node(node_id).get_graph()

        return GraphResult(
            graph=subgraph,
            variables_map=self.variables_map,
            consumer_results={
                component_id: consumer_result
                for component_id, consumer_result in self.consumer_results.items()
                if component_id in subgraph
            },
            emission_results={
                component_id: emissions
                for component_id, emissions in self.emission_results.items()
                if component_id in subgraph
            },
        )

    def get_energy_result(self, component_id: str) -> ComponentResult:
        return self.consumer_results[component_id]

    @property
    def periods(self):
        return self.variables_map.periods

    def get_emissions(self, component_id: str) -> dict[str, TimeSeriesStreamDayRate]:
        return self.emission_results[component_id]
