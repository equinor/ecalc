from libecalc.energy.energy_types import MechanicalPower


def compressor_shaft_power(gas_power_mw: float, mechanical_efficiency: float) -> MechanicalPower:
    """
    Shaft power a compressor demands from its drive train, given the power delivered to the gas by its process
    simulation [MW] and its mechanical efficiency in (0, 1], which covers the losses in its bearings and seals.
    """
    return MechanicalPower(gas_power_mw / mechanical_efficiency)
