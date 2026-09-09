from libecalc.energy.consumer import Consumer
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower


class ElectricalConsumer(Consumer):
    """Consumes electrical power."""

    @classmethod
    def get_input_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower


class MechanicalConsumer(Consumer):
    """Consumes mechanical power."""

    @classmethod
    def get_input_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower


class FuelGasConsumer(Consumer):
    """Consumes fuel gas."""

    @classmethod
    def get_input_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate


class DieselConsumer(Consumer):
    """Consumes diesel."""

    @classmethod
    def get_input_energy_type(cls) -> type[DieselRate]:
        return DieselRate
