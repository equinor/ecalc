from uuid import UUID

from libecalc.common.component_type import ComponentType
from libecalc.domain.energy import EnergyComponent
from libecalc.domain.infrastructure.energy_components.installation.installation import InstallationComponent


class Asset(EnergyComponent):
    def __init__(
        self,
        id: UUID,
        name: str,
        installations: list[InstallationComponent],
    ):
        self._uuid = id
        self._name = name
        self.installations = installations
        self.component_type = ComponentType.ASSET

    def get_id(self) -> UUID:
        return self._uuid

    @property
    def name(self):
        return self._name

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
