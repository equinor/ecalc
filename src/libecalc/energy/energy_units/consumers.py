import abc

from libecalc.common.errors.exceptions import IllegalStateException
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

    reports_power is set once by the caller (which already knows FILE's topology)
    rather than re-derived from compressor state on every get_energy() call:
    - False: energy_usage_values already are what this consumer demands (fuel, or
      power for a POWER-only compressor).
    - True: energy_usage_values are fuel, consumed by a separate dedicated turbine
      (see build_gas_turbine) - this consumer demands that turbine's resolved power
      instead.
    """

    def __init__(
        self,
        name: str,
        compressor: SampledCompressor,
        reports_power: bool = False,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, energy_unit_id)
        if reports_power and compressor.get_fuel_power_samples() is None:
            raise IllegalStateException(
                f"'{name}': reports_power=True requires the compressor to have "
                "power_interpolation_values to resolve a power value from."
            )
        self._compressor = compressor
        self._reports_power = reports_power

    def get_compressor(self) -> SampledCompressor:
        return self._compressor

    def get_energy(
        self,
        rate: float | None = None,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        result = self._compressor.evaluate(rate, suction_pressure, discharge_pressure)
        if self._reports_power:
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
