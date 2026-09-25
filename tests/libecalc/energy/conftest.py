from collections.abc import Mapping, Sequence

import pytest

from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.energy import Energy, EnergyUnit, EnergyUnitId
from libecalc.energy.dispatch import DispatchStrategy
from libecalc.energy.energy_network_simulation import EnergyNetworkSimulation, EnergyUnitFactory
from libecalc.energy.energy_network_topology import EnergyConnection, EnergyNetworkTopology
from libecalc.energy.energy_units import Junction


class NoOpEnergyUnitFactory[T: EnergyUnit](EnergyUnitFactory):
    """Fixed-configuration factory; also provides node metadata for consumers not created by the simulation."""

    def __init__(
        self,
        unit_class: type[T],
        name: str,
        *,
        input_energy_type: type[Energy] | None = None,
        **kwargs,
    ) -> None:
        self._unit_class = unit_class
        self._id = EnergyUnitId(ecalc_id_generator())
        self._name = name
        # Consumer's energy type is derived from its demand instance rather than being fixed on the class, so it
        # can't be read off the class the way the other (per-type) EnergyUnit subclasses allow; callers wrapping a
        # Consumer must state the type explicitly.
        self._input_energy_type = input_energy_type
        self._kwargs = kwargs

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_input_energy_type(self) -> type[Energy] | None:
        if self._input_energy_type is not None:
            return self._input_energy_type
        # Most EnergyUnit subclasses still expose a fixed energy type via a classmethod override, callable on the
        # class itself before any instance exists; basedpyright can't see that from the instance-method signature.
        return self._unit_class.get_input_energy_type()  # pyright: ignore[reportCallIssue]

    def get_output_energy_type(self) -> type[Energy] | None:
        if self._input_energy_type is not None:
            # Only Consumer (a terminal/leaf node) needs an explicit input-type override, and it never has an
            # output energy type since it doesn't feed anything downstream.
            return None
        return self._unit_class.get_output_energy_type()  # pyright: ignore[reportCallIssue]

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: object) -> T:
        connection_kwargs = {}
        if self.get_input_energy_type() is not None:
            (incoming_connection,) = incoming_connections
            connection_kwargs["input_connection_id"] = incoming_connection.id
        # Consumer names its value "demand" (it has no downstream output); every other EnergyUnit subclass
        # names it "output_energy".
        value_kwarg = "demand" if self._input_energy_type is not None else "output_energy"
        return self._unit_class(
            name=self.get_name(),
            energy_unit_id=self._id,
            **{value_kwarg: demand},
            **connection_kwargs,
            **self._kwargs,
        )


class NoOpJunctionFactory[T: Junction](EnergyUnitFactory):
    """Creates a junction with fixed dispatch configuration for any operating point."""

    def __init__(
        self,
        junction_class: type[T],
        name: str,
        dispatch_strategy: DispatchStrategy,
        input_capacities: Mapping[EnergyUnitId, Energy] | None = None,
    ) -> None:
        self._junction_class = junction_class
        self._id = EnergyUnitId(ecalc_id_generator())
        self._name = name
        self._dispatch_strategy = dispatch_strategy
        self._input_capacities = dict(input_capacities or {})

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_input_energy_type(self) -> type[Energy]:
        return self._junction_class.get_input_energy_type()

    def get_output_energy_type(self) -> type[Energy]:
        return self._junction_class.get_output_energy_type()

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: object) -> T:
        return self._junction_class(
            name=self._name,
            output_energy=demand,
            input_connection_ids={connection.source_id: connection.id for connection in incoming_connections},
            dispatch_strategy=self._dispatch_strategy,
            input_capacities=self._input_capacities,
            energy_unit_id=self._id,
        )


@pytest.fixture
def energy_unit_factory_factory():
    def build[T: EnergyUnit](c: type[T], name: str, **kwargs):
        return NoOpEnergyUnitFactory[T](c, name, **kwargs)

    return build


@pytest.fixture
def junction_factory_factory():
    def build[T: Junction](
        c: type[T],
        name: str,
        dispatch_strategy: DispatchStrategy,
        input_capacities: Mapping[EnergyUnitId, Energy] | None = None,
    ):
        return NoOpJunctionFactory[T](c, name, dispatch_strategy=dispatch_strategy, input_capacities=input_capacities)

    return build


@pytest.fixture
def energy_network_simulation_factory():
    def build(
        energy_unit_factories: list[EnergyUnitFactory],
        topology: EnergyNetworkTopology,
    ) -> EnergyNetworkSimulation:
        return EnergyNetworkSimulation(
            topology=topology,
            energy_unit_factories=energy_unit_factories,
        )

    return build
