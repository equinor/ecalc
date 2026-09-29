from collections.abc import Iterable

from libecalc.common.time_utils import Period
from libecalc.energy.energy_network_simulation import EnergyNetworkSimulation
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory


def create_simulation_for_period(
    topology: EnergyNetworkTopology, energy_unit_factories: Iterable[TimeSeriesEnergyUnitFactory], period: Period
) -> EnergyNetworkSimulation:
    return EnergyNetworkSimulation(
        topology=topology, energy_unit_factories=[factory.resolve(period) for factory in energy_unit_factories]
    )
