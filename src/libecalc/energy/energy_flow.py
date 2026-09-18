from libecalc.common.ddd import value_object
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy


@value_object
class EnergyFlow:
    connection: EnergyConnection
    energy: Energy
