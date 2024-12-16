from typing import Literal

from pydantic import Field

from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import generate_id
from libecalc.domain.infrastructure.energy_components.base.component_dto import Component
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.utils.validators import ComponentNameStr


class Asset(Component, EnergyComponent):
    @property
    def id(self):
        return generate_id(self.name)

    name: ComponentNameStr

    installations: list[Installation] = Field(default_factory=list)
    component_type: Literal[ComponentType.ASSET] = ComponentType.ASSET

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        # Should maybe be True if power from shore?
        return False

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return True

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
