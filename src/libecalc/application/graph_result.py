from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from libecalc.common.utils.rates import TimeSeries
from libecalc.common.variables import VariablesMap
from libecalc.core.result import ComponentResult, EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.component_graph import ComponentGraph


def serialize_datetime(v):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(v, list):
        return [serialize_datetime(item) for item in v]
    elif isinstance(v, dict):
        return {str(k): serialize_datetime(vv) for k, vv in v.items()}
    elif isinstance(v, BaseModel):
        return {str(k): serialize_datetime(getattr(v, k)) for k in v.model_fields}
    elif isinstance(v, TimeSeries):
        return {
            "periods": serialize_datetime(v.periods),
            "values": serialize_datetime(v.values),
            "unit": serialize_datetime(v.unit),
        }
    elif hasattr(v, "to_dict"):
        return serialize_datetime(v.to_dict())
    return v


class EnergyCalculatorResult(BaseModel):
    consumer_results: dict[str, EcalcModelResult] = Field(default_factory=dict)
    emission_results: dict[str, dict[str, EmissionResult]]
    variables_map: VariablesMap

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["consumer_results"] = {k: serialize_datetime(v) for k, v in self.consumer_results.items()}
        data["emission_results"] = {
            k: {ek: serialize_datetime(ev) for ek, ev in v.items()} for k, v in self.emission_results.items()
        }
        data["variables_map"] = serialize_datetime(self.variables_map)
        return data


class GraphResult:
    def __init__(
        self,
        graph: ComponentGraph,
        consumer_results: dict[str, EcalcModelResult],
        emission_results: dict[str, dict[str, EmissionResult]],
        variables_map: VariablesMap,
    ):
        self.graph = graph
        self.consumer_results = consumer_results
        self.emission_results = emission_results
        self.variables_map = variables_map

    def get_subgraph(self, node_id: str) -> "GraphResult":
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
        return self.consumer_results[component_id].component_result

    @property
    def periods(self):
        return self.variables_map.periods

    def get_emissions(self, component_id: str) -> dict[str, EmissionResult]:
        return self.emission_results[component_id]

    def get_results(self) -> EnergyCalculatorResult:
        return EnergyCalculatorResult(
            consumer_results=self.consumer_results,
            emission_results=self.emission_results,
            variables_map=self.variables_map,
        )
