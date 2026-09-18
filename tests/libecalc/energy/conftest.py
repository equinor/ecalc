import pytest

from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.energy import Energy, EnergyUnit, EnergyUnitId
from libecalc.energy.energy_network_simulation import EnergyNetworkSimulation, EnergyUnitFactory
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
from libecalc.energy.energy_units import Junction


class NoOpEnergyUnitFactory[T: EnergyUnit](EnergyUnitFactory):
    def __init__(self, unit_class: type[T], name: str, **kwargs) -> None:
        self._unit_class = unit_class
        self._id = EnergyUnitId(ecalc_id_generator())
        self._name = name
        self._kwargs = kwargs

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_input_energy_type(self) -> type[Energy] | None:
        return self._unit_class.get_input_energy_type()

    def get_output_energy_type(self) -> type[Energy] | None:
        return self._unit_class.get_output_energy_type()

    def create(self, demand: Energy, capacity: Energy | None, **extra: object) -> T:
        unit = self._unit_class(name=self.get_name(), output_energy=demand, capacity=capacity, **self._kwargs)
        return unit


@pytest.fixture
def energy_unit_factory_factory():
    def build[T](c: type[T], name: str, **kwargs):
        return NoOpEnergyUnitFactory[T](c, name, **kwargs)

    return build


@pytest.fixture
def energy_network_simulation_factory():

    def build(
        junctions: list[Junction],
        energy_unit_factories: list[EnergyUnitFactory],
        topology: EnergyNetworkTopology,
    ) -> EnergyNetworkSimulation:
        return EnergyNetworkSimulation(
            topology=topology,
            energy_unit_factories=energy_unit_factories,
            junctions={junction.get_id(): junction for junction in junctions},
        )

    return build
