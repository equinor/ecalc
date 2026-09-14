import abc

from libecalc.energy.consumer import Consumer
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.models.sampled_compressor import SampledCompressor


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


class SampledCompressorConsumerBase(Consumer, abc.ABC):
    """Terminal consumer wrapping a SampledCompressor model.

    Holds the compressor's operating point (rate, suction_pressure, discharge_pressure)
    -> energy usage lookup. When the compressor has power_interpolation_values (i.e. a
    dedicated turbine converts its fuel usage into mechanical power), get_energy reports
    that power - the compressor's own energy_usage_values are fuel in that case, not what
    this consumer demands. Otherwise, get_energy reports the compressor's energy usage
    directly: for a directly fuel-driven compressor that's the fuel itself; for a
    POWER-only compressor (driven by an electrical motor or by mechanical input), the
    sampled energy usage values already are the power this consumer demands.
    """

    def __init__(
        self,
        name: str,
        compressor: SampledCompressor,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, energy_unit_id)
        self._compressor = compressor

    def get_compressor(self) -> SampledCompressor:
        return self._compressor

    def get_energy(
        self,
        rate: float | None = None,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        result = self._compressor.evaluate(rate, suction_pressure, discharge_pressure)
        if self._compressor.get_fuel_power_samples() is not None:
            assert result.power is not None
            return result.power
        return result.energy_usage


class SampledCompressorFuelGasConsumer(SampledCompressorConsumerBase):
    """A SampledCompressor consuming fuel gas directly (no dedicated turbine)."""

    @classmethod
    def get_input_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate


class SampledCompressorElectricalConsumer(SampledCompressorConsumerBase):
    """A SampledCompressor driven by an electrical motor."""

    @classmethod
    def get_input_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower


class SampledCompressorMechanicalConsumer(SampledCompressorConsumerBase):
    """A SampledCompressor driven by mechanical power, e.g. from its own dedicated turbine."""

    @classmethod
    def get_input_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower
