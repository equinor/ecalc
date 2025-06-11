import abc

from libecalc.domain.energy.energy_component import EnergyComponent
from libecalc.domain.process.temporal_process_system import TemporalProcessSystem


class EnergyModel(abc.ABC):
    """
    Energy model contains energy components which can be consumers, providers, emitters
    """

    @abc.abstractmethod
    def get_consumers(self, provider_id: str = None) -> list[EnergyComponent]:
        """
        Get consumers of the given provider. If no provider is given, assume top-level.
        """
        ...

    @abc.abstractmethod
    def get_energy_components(self) -> list[EnergyComponent]:
        """
        Get a sorted list of energy components
        """
        ...

    @abc.abstractmethod
    def get_process_systems(self) -> list[TemporalProcessSystem]:
        """
        Get a sorted list of process systems.
        """
        ...
