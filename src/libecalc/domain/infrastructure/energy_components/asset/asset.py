from libecalc.common.component_type import ComponentType
from libecalc.domain.energy import EnergyComponent
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.dto.component_graph import ComponentGraph


class Asset(EnergyComponent):
    def __init__(
        self,
        path_id: PathID,
        installations: list[Installation],
    ):
        self._path_id = path_id
        self.installations = installations
        self.component_type = ComponentType.ASSET

    @property
    def id(self):
        return self._path_id.get_name()

    @property
    def name(self):
        return self._path_id.get_name()

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        # Should maybe be True if power from shore?
        return False

    def is_provider(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for installation in self.installations:
            graph.add_subgraph(installation.get_graph())
            graph.add_edge(self.id, installation.id)

        return graph
