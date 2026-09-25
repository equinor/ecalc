import abc
from collections.abc import Mapping

from libecalc.energy.dispatch import Candidate, DispatchStrategy
from libecalc.energy.energy_failure import EnergyFailure
from libecalc.energy.energy_types import ElectricalPower, Energy, FuelGasRate
from libecalc.energy.energy_unit import EnergyUnit
from libecalc.energy.ids import EnergyConnectionId, EnergyUnitId


class Junction(EnergyUnit):
    """Lossless junction whose strategy splits total demand across at least two inputs of the same energy type.

    Input limits are measured after upstream conversion and losses; they guide dispatch rather than cap demand.
    Missing limits are unlimited. Supplying units report overloads against their own ratings.
    """

    def __init__(
        self,
        name: str,
        output_energy: Energy,
        *,
        input_connection_ids: Mapping[EnergyUnitId, EnergyConnectionId],
        dispatch_strategy: DispatchStrategy,
        input_capacities: Mapping[EnergyUnitId, Energy],
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, energy_unit_id)
        self._output_energy = output_energy
        self._input_connection_ids = dict(input_connection_ids)
        self._dispatch_strategy = dispatch_strategy
        self._input_capacities = dict(input_capacities)
        assert len(self._input_connection_ids) >= 2, "A junction requires at least two inputs"
        assert dispatch_strategy.get_candidate_ids() == self._input_connection_ids.keys()
        assert self._input_capacities.keys() <= self._input_connection_ids.keys()
        assert all(type(capacity) is self.get_energy_type() for capacity in self._input_capacities.values())

    def get_output_energy(self) -> Energy:
        return self._output_energy

    def get_input_energies(self) -> dict[EnergyConnectionId, Energy]:
        candidates = tuple(
            Candidate(candidate_id=candidate_id, available=self._input_capacities.get(candidate_id))
            for candidate_id in self._input_connection_ids
        )
        allocation = self._dispatch_strategy.allocate(demand=self._output_energy, candidates=candidates)
        assert allocation.keys() == self._input_connection_ids.keys()
        return {self._input_connection_ids[candidate_id]: share for candidate_id, share in allocation.items()}

    def get_failures(self) -> list[EnergyFailure]:
        # Input capacities are dispatch limits, not ratings; a physical limit is reported by the supplying unit.
        return []

    @classmethod
    @abc.abstractmethod
    def get_energy_type(cls) -> type[Energy]: ...

    @classmethod
    def get_input_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    @classmethod
    def get_output_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()


class ElectricalBus(Junction):
    """Electrical power distribution bus (busbar)."""

    @classmethod
    def get_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower


class FuelGasManifold(Junction):
    """Fuel gas distribution manifold (header)."""

    @classmethod
    def get_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate
