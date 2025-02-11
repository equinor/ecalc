from datetime import datetime

from libecalc.domain.energy import EnergyComponent, EnergyModel
from libecalc.expression import Expression


class DTOEnergyModel(EnergyModel):
    def get_regularity(self, component_id: str) -> dict[datetime, Expression]:
        graph = self.component.get_graph()
        installation_id = graph.get_parent_installation_id(component_id)
        installation = graph.get_node(installation_id)
        return installation.regularity

    def get_consumers(self, provider_id: str = None) -> list[EnergyComponent]:
        return self.component.get_graph().get_consumers(provider_id)

    def get_energy_components(self) -> list[EnergyComponent]:
        return self.component.get_graph().get_energy_components()

    def __init__(self, component):
        self.component = component
