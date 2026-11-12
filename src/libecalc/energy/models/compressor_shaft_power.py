from libecalc.energy.energy_types import MechanicalPower


def compressor_shaft_power(gas_power_mw: float, mechanical_efficiency: float) -> MechanicalPower:
    """
    Shaft power a compressor demands from its driver, given the power delivered to the gas by its process
    simulation [MW] and its mechanical efficiency in (0, 1]. The efficiency covers the losses in the compressor's
    bearings and seals and its share of the gearbox and couplings, not the driver's own losses.
    """
    return MechanicalPower(gas_power_mw / mechanical_efficiency)
