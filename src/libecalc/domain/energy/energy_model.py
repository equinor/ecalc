import abc
from collections.abc import Sequence

from libecalc.domain.energy import EnergyComponent
from libecalc.domain.energy.energy_component import EnergyContainerID


class EnergyModel(abc.ABC):
    """
    Energy model contains energy components which can be consumers, providers, emitters
    """

    @abc.abstractmethod
    def get_consumers(self, provider_id: EnergyContainerID) -> list[EnergyContainerID]:
        """
        Get direct consumers of the given provider.
        """
        ...

    @abc.abstractmethod
    def get_energy_components(self) -> Sequence[EnergyContainerID]:
        """
        Get a sorted list of energy components
        """
        ...

    @abc.abstractmethod
    def get_energy_container(self, container_id: EnergyContainerID) -> EnergyComponent: ...

    @abc.abstractmethod
    def get_parent(self, container_id: EnergyContainerID) -> EnergyContainerID: ...

    @abc.abstractmethod
    def get_root(self) -> EnergyContainerID: ...
