"""Unit tests for energy_units components."""

from uuid import UUID

import pytest

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.energy import Consumer, Source
from libecalc.energy.energy_types import (
    DieselRate,
    ElectricalPower,
    Energy,
    FuelGasRate,
    MechanicalPower,
)
from libecalc.energy.energy_units import (
    DieselConsumer,
    DieselSource,
    ElectricalCable,
    ElectricalConsumer,
    ElectricalMotor,
    ElectricalSource,
    FuelGasConsumer,
    FuelGasSource,
    GasTurbine,
    GeneratorSet,
    MechanicalConsumer,
    SampledCompressorElectricalConsumer,
    SampledCompressorFuelGasConsumer,
    SampledCompressorMechanicalConsumer,
)
from libecalc.energy.models.sampled_compressor import SampledCompressor


class TestSources:
    @pytest.mark.parametrize(
        ("source", "expected_output_type"),
        [
            (FuelGasSource("fuel"), FuelGasRate),
            (DieselSource("diesel"), DieselRate),
            (ElectricalSource("electricity"), ElectricalPower),
        ],
    )
    def test_source_energy_contract(
        self,
        source: Source,
        expected_output_type: type[Energy],
    ):
        assert source.get_input_energy_type() is None
        assert source.get_output_energy_type() is expected_output_type
        assert isinstance(source.get_id(), UUID)


class TestConverters:
    def test_electrical_cable_accounts_for_loss(self):
        cable = ElectricalCable("cable", loss_fraction=0.04)
        result = cable.get_input_energy(ElectricalPower(10.0))
        assert result.value == pytest.approx(10.0 / 0.96)

    def test_generator_set_applies_fuel_curve(self):
        genset = GeneratorSet("gs1", power_to_fuel=lambda mw: 5000 + mw * 4500)
        result = genset.get_input_energy(ElectricalPower(10.0))
        assert result == FuelGasRate(5000 + 10 * 4500)

    def test_gas_turbine_applies_fuel_curve(self):
        turbine = GasTurbine("t1", power_to_fuel=lambda mw: 3000 + mw * 3500)
        result = turbine.get_input_energy(MechanicalPower(15.0))
        assert result == FuelGasRate(3000 + 15 * 3500)

    def test_electrical_motor_divides_by_efficiency(self):
        motor = ElectricalMotor("m1", efficiency=0.93)
        result = motor.get_input_energy(MechanicalPower(7.0))
        assert result.value == pytest.approx(7.0 / 0.93)
        assert isinstance(result, ElectricalPower)


class TestConsumers:
    @pytest.mark.parametrize(
        ("consumer", "expected_input_type"),
        [
            (ElectricalConsumer("electrical_consumer"), ElectricalPower),
            (MechanicalConsumer("compressor"), MechanicalPower),
            (DieselConsumer("diesel_consumer"), DieselRate),
            (FuelGasConsumer("fuel_consumer"), FuelGasRate),
        ],
    )
    def test_consumer_energy_contract(
        self,
        consumer: Consumer,
        expected_input_type: type[Energy],
    ):
        assert consumer.get_input_energy_type() is expected_input_type
        assert consumer.get_output_energy_type() is None
        assert isinstance(consumer.get_id(), UUID)


class TestSampledCompressorConsumers:
    @staticmethod
    def _fuel_only_compressor() -> SampledCompressor:
        return SampledCompressor(
            energy_usage_values=[1000.0, 2000.0, 3000.0],
            rate_values=[0.0, 100.0, 200.0],
        )

    @staticmethod
    def _fuel_and_turbine_compressor() -> SampledCompressor:
        return SampledCompressor(
            energy_usage_values=[1000.0, 2000.0, 3000.0],
            rate_values=[0.0, 100.0, 200.0],
            power_interpolation_values=[1.0, 2.0, 3.0],
        )

    @pytest.mark.parametrize(
        ("consumer_type", "expected_input_type"),
        [
            (SampledCompressorFuelGasConsumer, FuelGasRate),
            (SampledCompressorElectricalConsumer, ElectricalPower),
            (SampledCompressorMechanicalConsumer, MechanicalPower),
        ],
    )
    def test_energy_contract(self, consumer_type: type[Consumer], expected_input_type: type[Energy]):
        consumer = consumer_type("compressor", self._fuel_only_compressor())
        assert consumer.get_input_energy_type() is expected_input_type
        assert consumer.get_output_energy_type() is None
        assert isinstance(consumer.get_id(), UUID)

    def test_fuel_gas_consumer_reads_energy_usage_directly(self):
        consumer = SampledCompressorFuelGasConsumer("compressor", self._fuel_only_compressor())
        assert consumer.get_energy(rate=50.0) == pytest.approx(1500.0)

    def test_electrical_consumer_reads_power(self):
        compressor = SampledCompressor(
            energy_usage_values=[1.0, 2.0, 3.0],
            rate_values=[0.0, 100.0, 200.0],
        )
        consumer = SampledCompressorElectricalConsumer("compressor", compressor)
        assert consumer.get_energy(rate=50.0) == pytest.approx(1.5)

    def test_mechanical_consumer_reads_power_from_turbine_compressor(self):
        consumer = SampledCompressorMechanicalConsumer(
            "compressor", self._fuel_and_turbine_compressor(), reports_power=True
        )
        assert consumer.get_energy(rate=50.0) == pytest.approx(1.5)

    def test_mechanical_consumer_without_power_interpolation_reads_energy_usage_directly(self):
        # No power_interpolation_values means this compressor's own energy_usage_values
        # already are power - e.g. a POWER-only compressor driven directly by a
        # GAS_TURBINE/ELECTRICAL_MOTOR unit upstream, with no dedicated turbine of its own.
        consumer = SampledCompressorMechanicalConsumer("compressor", self._fuel_only_compressor())
        assert consumer.get_energy(rate=50.0) == pytest.approx(1500.0)

    def test_reports_power_true_without_power_interpolation_raises(self):
        with pytest.raises(IllegalStateException, match="reports_power=True requires"):
            SampledCompressorMechanicalConsumer("compressor", self._fuel_only_compressor(), reports_power=True)
