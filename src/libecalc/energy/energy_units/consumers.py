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
    """Terminal consumer wrapping a SampledCompressor model."""

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
        return self._compressor.evaluate(rate, suction_pressure, discharge_pressure).energy_usage


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
    """A SampledCompressor driven by mechanical power, e.g. from its own dedicated turbine.

    energy_usage_values may already be power, or may be fuel consumed by a separate
    dedicated turbine (see build_gas_turbine), in which case this consumer must
    instead demand the resolved power from get_energy() - determined per call from
    the result itself: power is only ever resolved when FILE had both FUEL and
    POWER, which is exactly the "fuel consumed, power reported" case.
    """

    @classmethod
    def get_input_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower

    def get_energy(
        self,
        rate: float | None = None,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        result = self._compressor.evaluate(rate, suction_pressure, discharge_pressure)
        return result.power if result.power is not None else result.energy_usage
