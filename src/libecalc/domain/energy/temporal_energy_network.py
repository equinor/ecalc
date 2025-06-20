import abc

from libecalc.domain.energy.energy_network import EnergyChangedEvent, EnergyNetwork


class TemporalEnergyNetwork(abc.ABC):
    @abc.abstractmethod
    def get_energy_changed_events(self) -> list[EnergyChangedEvent]: ...

    @abc.abstractmethod
    def get_energy_network(self, event: EnergyChangedEvent) -> EnergyNetwork: ...
