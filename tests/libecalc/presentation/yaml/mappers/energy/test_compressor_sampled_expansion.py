import math

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.presentation.yaml.mappers.energy.compressor_sampled_expansion import (
    DemandSource,
    expand,
    load_model,
    turbine_key,
    unit_key,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlCompressorSampled


def _unit(**overrides) -> YamlCompressorSampled:
    data = {"NAME": "compressor", "TYPE": "COMPRESSOR_SAMPLED", "INPUT": "fuel", "FILE": "comp.csv", "RATE": 2500}
    data.update(overrides)
    return YamlCompressorSampled.model_validate(data)


class TestLoadModel:
    @pytest.mark.parametrize(
        "resource_kwargs, expected_columns, expected_usage, expected_power",
        [
            ({"FUEL": True}, (True, False), 15000, None),
            ({"POWER": True}, (False, True), 7.5, None),
            ({"FUEL": True, "POWER": True}, (True, True), 15000, 7.5),
        ],
    )
    def test_energy_usage_and_power_from_columns(
        self, resource_kwargs, expected_columns, expected_usage, expected_power, make_resource, rates, fuel, power
    ):
        column_values = {"FUEL": fuel, "POWER": power}
        resource = make_resource(RATE=rates, **{col: column_values[col] for col in resource_kwargs})
        model, columns = load_model(resource)
        assert (columns.has_fuel, columns.has_power) == expected_columns
        result = model.evaluate(rate=1500)
        assert result.energy_usage == pytest.approx(expected_usage)
        assert result.power == (pytest.approx(expected_power) if expected_power is not None else None)

    def test_neither_fuel_nor_power_rejected(self, make_resource, rates):
        with pytest.raises(EcalcValidationException, match="FUEL and/or POWER column"):
            load_model(make_resource(RATE=rates, SUCTION_PRESSURE=[10.0, 20.0, 30.0]))


class TestExpandSingleConsumer:
    @pytest.mark.parametrize(
        "input_name, resource_kwargs, upstream, expected_usage",
        [
            ("fuel", {"FUEL": True}, FuelGasRate, 25000),
            ("genset", {"POWER": True}, ElectricalPower, 12.5),
            ("genset", {"POWER": True}, MechanicalPower, 12.5),
        ],
    )
    def test_single_consumer_typed_after_upstream(
        self, input_name, resource_kwargs, upstream, expected_usage, make_resource, rates, fuel, power
    ):
        column_values = {"FUEL": fuel, "POWER": power}
        resource = make_resource(RATE=rates, **{col: column_values[col] for col in resource_kwargs})
        unit = _unit(INPUT=input_name)
        expansion = expand(unit, resource, upstream)

        assert len(expansion.nodes) == 1
        consumer = expansion.nodes[0]
        assert consumer.key == unit_key("compressor")
        assert consumer.name == "compressor"
        assert expansion.connections == ((unit_key(input_name), consumer.key),)
        assert consumer.input_energy_type is upstream
        assert consumer.demand_source is DemandSource.ENERGY_USAGE
        assert consumer.model.evaluate(rate=2500).energy_usage == pytest.approx(expected_usage)

    @pytest.mark.parametrize(
        "resource_kwargs, upstream, match",
        [
            ({"FUEL": True}, ElectricalPower, "must be fed FuelGasRate.*'fuel' provides ElectricalPower"),
            ({"POWER": True}, FuelGasRate, "power-driven compressor must be fed"),
            ({"POWER": True}, DieselRate, "power-driven compressor must be fed"),
            ({"FUEL": True, "POWER": True}, ElectricalPower, "generated turbine must be fed FuelGasRate"),
        ],
    )
    def test_rejects_incompatible_upstream(self, resource_kwargs, upstream, match, make_resource, rates, fuel, power):
        column_values = {"FUEL": fuel, "POWER": power}
        resource = make_resource(RATE=rates, **{col: column_values[col] for col in resource_kwargs})
        with pytest.raises(EcalcValidationException, match=match):
            expand(_unit(), resource, upstream)


class TestExpandFuelAndPower:
    def test_turbine_driven(self, make_resource, rates, fuel, power):
        unit = _unit()
        expansion = expand(unit, make_resource(RATE=rates, FUEL=fuel, POWER=power), FuelGasRate)

        assert len(expansion.nodes) == 2
        turbine, consumer = expansion.nodes

        assert turbine.key == turbine_key("compressor")
        assert turbine.name == "compressor turbine"
        assert consumer.key == unit_key("compressor")
        assert expansion.connections == ((unit_key("fuel"), turbine.key), (turbine.key, consumer.key))
        assert consumer.input_energy_type is MechanicalPower
        assert consumer.demand_source is DemandSource.POWER

        result = consumer.model.evaluate(rate=2500)
        assert result.power == pytest.approx(12.5)
        assert turbine.fuel_power_curve.fuel_for_power(12.5) == pytest.approx(25000)

    def test_rejects_non_invertible_fuel_power_table(self, make_resource, rates, fuel):
        with pytest.raises(EcalcValidationException, match="'compressor'.*'comp.csv'.*strictly monotonic"):
            expand(_unit(), make_resource(RATE=rates, FUEL=fuel, POWER=[5.0, 5.0, 15.0]), FuelGasRate)


class TestExpandVariables:
    def test_given_variable_not_tabulated_rejected(self, make_resource, rates, fuel):
        with pytest.raises(EcalcValidationException, match="SUCTION_PRESSURE given, but not tabulated"):
            expand(_unit(SUCTION_PRESSURE=20), make_resource(RATE=rates, FUEL=fuel), FuelGasRate)

    def test_tabulated_variable_not_given_rejected(self, make_resource):
        resource = make_resource(
            RATE=[1000.0, 2000.0, 1000.0, 2000.0],
            SUCTION_PRESSURE=[10.0, 10.0, 20.0, 20.0],
            FUEL=[10000.0, 20000.0, 15000.0, 30000.0],
        )
        with pytest.raises(EcalcValidationException, match="tabulates SUCTION_PRESSURE, which must be given"):
            expand(_unit(), resource, FuelGasRate)


class TestFuelPowerCurve:
    def test_inverts_samples_and_handles_bounds(self, make_resource, rates, fuel, power):
        model, _ = load_model(make_resource(RATE=rates, FUEL=fuel, POWER=power))
        curve = model.get_fuel_power_curve()
        assert curve is not None

        assert curve.fuel_for_power(0) == 0.0
        assert curve.fuel_for_power(2.0) == pytest.approx(10000)
        assert curve.fuel_for_power(7.5) == pytest.approx(15000)
        assert math.isnan(curve.fuel_for_power(20.0))

    def test_power_for_fuel_is_the_inverse(self, make_resource, rates, fuel, power):
        model, _ = load_model(make_resource(RATE=rates, FUEL=fuel, POWER=power))
        curve = model.get_fuel_power_curve()
        assert curve is not None

        assert curve.power_for_fuel(0) == 0.0
        assert curve.power_for_fuel(15000) == pytest.approx(7.5)

    def test_requires_power_samples(self, make_resource, rates, fuel):
        model, _ = load_model(make_resource(RATE=rates, FUEL=fuel))
        assert model.get_fuel_power_curve() is None


class TestYamlCompressorSampled:
    def test_requires_a_lookup_variable(self):
        with pytest.raises(ValueError, match="at least one of RATE, SUCTION_PRESSURE or DISCHARGE_PRESSURE"):
            YamlCompressorSampled.model_validate(
                {"NAME": "c", "TYPE": "COMPRESSOR_SAMPLED", "INPUT": "fuel", "FILE": "comp.csv"}
            )

    def test_negative_rate_rejected(self):
        with pytest.raises(ValueError, match="RATE must be non-negative"):
            _unit(RATE=-1)
