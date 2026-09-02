"""Roles a node can take on in the energy network: sink (Consumer), source (Source), or pass-through
(DerivedInputProvider and its subclasses). A role is about how a node's input/output energy is computed,
not what physical equipment it represents - the same equipment could in principle be modeled differently."""

from __future__ import annotations

import abc

from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId


class Consumer(EnergyUnit, abc.ABC):
    """Anything with a fixed, self-determined input demand."""

    @classmethod
    @abc.abstractmethod
    def get_input_energy_type(cls) -> type[Energy]: ...

    @abc.abstractmethod
    def get_input_energy(self) -> Energy: ...


class Provider(EnergyUnit, abc.ABC):
    """Anything that supplies energy."""

    @classmethod
    @abc.abstractmethod
    def get_output_energy_type(cls) -> type[Energy]: ...

    @abc.abstractmethod
    def capacity(self) -> Energy | None: ...


class Source(Provider):
    """A provider with no input of its own - energy enters the system from outside the network here."""

    ...


class DerivedInputProvider(Provider, abc.ABC):
    """A provider whose input is computed from the output it's asked to deliver."""

    @classmethod
    @abc.abstractmethod
    def get_input_energy_type(cls) -> type[Energy]: ...

    @abc.abstractmethod
    def get_input_energy(self, requested_output: Energy) -> Energy: ...


class Converter(DerivedInputProvider):
    """Converts one energy type to another."""

    def get_input_energy(self, requested_output: Energy) -> Energy:
        return self._get_input_energy(requested_output)

    @abc.abstractmethod
    def _get_input_energy(self, output_energy: Energy) -> Energy: ...


class Transporter(DerivedInputProvider):
    """Moves energy without changing form, possibly with loss."""

    @classmethod
    @abc.abstractmethod
    def get_energy_type(cls) -> type[Energy]: ...

    @classmethod
    def get_input_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    @classmethod
    def get_output_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    def get_input_energy(self, requested_output: Energy) -> Energy:
        return self._get_input_energy(requested_output)

    @abc.abstractmethod
    def _get_input_energy(self, output_energy: Energy) -> Energy: ...


class Junction(DerivedInputProvider, abc.ABC):
    """Aggregation point for same-type energy; multi-predecessor allocation is not yet implemented."""

    def __init__(
        self, name: str, energy_unit_id: EnergyUnitId | None = None, max_predecessors: int | None = None
    ) -> None:
        super().__init__(name, energy_unit_id)
        self._max_predecessors = max_predecessors

    @classmethod
    @abc.abstractmethod
    def get_energy_type(cls) -> type[Energy]: ...

    @classmethod
    def get_input_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    @classmethod
    def get_output_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    def max_predecessors(self) -> int | None:
        """Maximum number of predecessors allowed; None means unlimited."""
        return self._max_predecessors

    def capacity(self) -> Energy | None:
        return None

    def get_input_energy(self, requested_output: Energy) -> Energy:
        return self._get_input_energy(requested_output)

    def _get_input_energy(self, output_energy: Energy) -> Energy:
        return output_energy  # lossless by default; override for lossy junctions
