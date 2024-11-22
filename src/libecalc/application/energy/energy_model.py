import abc
from datetime import datetime

from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.expression import Expression


class EnergyModel(abc.ABC):
    """
    Energy model contains energy components which can be consumers, providers, emitters
    """

    @abc.abstractmethod
    def get_regularity(self, component_id: str) -> dict[datetime, Expression]:
        """
        Temporary solution to get regularity since (dto) components don't have the necessary info to evaluate itself.
        """
        ...

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
