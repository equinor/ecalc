import pytest

from libecalc.common.errors.ecalc_validation_error import ProcessHeaderValidationException
from libecalc.presentation.yaml.mappers.energy.sampled_compressor_mapper import (
    build_sampled_compressor_model,
    validate_input_energy_type,
)
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import EnergyType


def _resource(headers: list[str], data: list[list[float]]) -> MemoryResource:
    """data is row-oriented (one row per sample point); MemoryResource stores columns."""
    columns = [list(column) for column in zip(*data)]
    return MemoryResource(headers=headers, data=columns)


class TestNeitherFuelNorPower:
    def test_raises_header_validation_error(self):
        resource = _resource(headers=["RATE", "SUCTION_PRESSURE"], data=[[1000, 20], [2000, 20]])
        with pytest.raises(ProcessHeaderValidationException, match="FUEL' or 'POWER'"):
            build_sampled_compressor_model(resource)


class TestFuelOnly:
    """Only FUEL present: a black-box turbine + compressor, energy usage interpolated
    directly as fuel."""

    def test_builds_compressor_without_turbine(self):
        resource = _resource(
            headers=["RATE", "FUEL"],
            data=[[1000, 100], [2000, 150], [3000, 200]],
        )
        model = build_sampled_compressor_model(resource)
        result = model.compressor.evaluate(rate=2000)
        assert result.energy_usage == pytest.approx(150)
        assert result.power is None
        assert model.consumes_fuel is True


class TestPowerOnly:
    """Only POWER present: a black-box motor + compressor, energy usage interpolated
    directly as power."""

    def test_builds_compressor_without_turbine(self):
        resource = _resource(
            headers=["RATE", "POWER"],
            data=[[1000, 1.0], [2000, 1.5], [3000, 2.0]],
        )
        model = build_sampled_compressor_model(resource)
        result = model.compressor.evaluate(rate=2000)
        assert result.energy_usage == pytest.approx(1.5)
        assert result.power is None
        assert model.consumes_fuel is False


class TestFuelAndPower:
    """Both FUEL and POWER present: energy usage is fuel, with POWER giving the
    corresponding turbine power. The compressor itself resolves both from a single
    evaluate() call; a GasTurbine for that resolved pair is only built later, from the
    resolved values (see build_sampled_compressor_consumer), not by this mapper."""

    def test_five_column_csv_resolves_fuel_and_power_together(self):
        resource = _resource(
            headers=["POWER", "FUEL", "RATE", "SUCTION_PRESSURE", "DISCHARGE_PRESSURE"],
            data=[
                [1.0, 100, 1000, 20, 60],
                [1.5, 150, 2000, 20, 60],
                [2.0, 200, 3000, 20, 60],
            ],
        )
        model = build_sampled_compressor_model(resource)

        # The compressor interpolates fuel usage directly, with power available too.
        result = model.compressor.evaluate(
            rate=2000,
            suction_pressure=20,
            discharge_pressure=60,
        )
        assert result.energy_usage == pytest.approx(150)
        assert result.power is not None
        assert result.power == pytest.approx(1.5)
        assert model.consumes_fuel is True


class TestValidateInputEnergyType:
    """A unit's declared INPUT must actually match what FILE provides - the YAML schema
    alone can't catch this, since it doesn't know FILE's columns."""

    def test_fuel_model_accepts_fuel_gas_input(self):
        resource = _resource(headers=["RATE", "FUEL"], data=[[1000, 100], [2000, 150]])
        model = build_sampled_compressor_model(resource)
        validate_input_energy_type("compressor", model, EnergyType.FUEL_GAS)

    def test_fuel_model_rejects_electrical_input(self):
        resource = _resource(headers=["RATE", "FUEL"], data=[[1000, 100], [2000, 150]])
        model = build_sampled_compressor_model(resource)
        with pytest.raises(ValueError, match="FUEL column"):
            validate_input_energy_type("compressor", model, EnergyType.ELECTRICAL)

    def test_power_model_accepts_electrical_input(self):
        resource = _resource(headers=["RATE", "POWER"], data=[[1000, 1.0], [2000, 1.5]])
        model = build_sampled_compressor_model(resource)
        validate_input_energy_type("compressor", model, EnergyType.ELECTRICAL)

    def test_power_model_rejects_fuel_gas_input(self):
        resource = _resource(headers=["RATE", "POWER"], data=[[1000, 1.0], [2000, 1.5]])
        model = build_sampled_compressor_model(resource)
        with pytest.raises(ValueError, match="POWER column"):
            validate_input_energy_type("compressor", model, EnergyType.FUEL_GAS)
