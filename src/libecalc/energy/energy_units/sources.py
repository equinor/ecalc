from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate
from libecalc.energy.source import Source


class FuelGasSource(Source):
    """Platform fuel gas supply, typically from the reservoir."""

    @classmethod
    def get_output_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate


class ElectricalSource(Source):
    """Source of electrical power"""

    @classmethod
    def get_output_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower


class DieselSource(Source):
    """Diesel fuel source, brought to platform/rig by supply vessels."""

    @classmethod
    def get_output_energy_type(cls) -> type[DieselRate]:
        return DieselRate
