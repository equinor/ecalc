import typing

import pytest

from libecalc.common.errors.ecalc_validation_error import ProcessHeaderValidationException
from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.presentation.yaml.mappers.energy.sampled_compressor_mapper import (
    _expand_sampled_compressor,
    build_sampled_compressor_model,
    expand_sampled_compressors,
    validate_input_energy_type,
)
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    EnergyType,
    YamlEnergyNetwork,
    YamlGasTurbine,
    YamlSampledCompressor,
    _SampledElectricalConsumer,
    _SampledFuelGasConsumer,
    _SampledGasTurbine,
    _SampledMechanicalConsumer,
)


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

    def test_fuel_only_energy_usage_is_interpolated_as_fuel(self):
        resource = _resource(
            headers=["RATE", "FUEL"],
            data=[[1000, 100], [2000, 150], [3000, 200]],
        )
        model = build_sampled_compressor_model(resource)
        # Between the 1000 -> 100 and 2000 -> 150 samples, so this genuinely interpolates
        # rather than returning a sample row verbatim.
        result = model.compressor.evaluate(rate=1500)
        assert result.energy_usage == pytest.approx(125.0)
        assert result.power is None
        assert model.consumes_fuel is True


class TestPowerOnly:
    """Only POWER present: a black-box motor + compressor, energy usage interpolated
    directly as power."""

    def test_power_only_energy_usage_is_power_and_no_turbine_power_is_resolved(self):
        resource = _resource(
            headers=["RATE", "POWER"],
            data=[[1000, 1.0], [2000, 1.5], [3000, 2.0]],
        )
        model = build_sampled_compressor_model(resource)
        result = model.compressor.evaluate(rate=1500)
        assert result.energy_usage == pytest.approx(1.25)
        # POWER is this compressor's own energy usage here, not a turbine's output, so no
        # separate power value is resolved alongside it.
        assert result.power is None
        assert model.consumes_fuel is False


class TestFuelAndPower:
    """Both FUEL and POWER present: energy usage is fuel, with POWER giving the
    corresponding turbine power. The compressor itself resolves both from a single
    evaluate() call; a GasTurbine for that resolved pair is only built later, from the
    resolved values (see _expand_sampled_compressor), not by this mapper."""

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
            rate=1500,
            suction_pressure=20,
            discharge_pressure=60,
        )
        assert result.energy_usage == pytest.approx(125.0)
        assert result.power is not None
        assert result.power == pytest.approx(1.25)
        assert model.consumes_fuel is True


class TestValidateInputEnergyType:
    """A unit's declared INPUT must actually match what FILE provides - the YAML schema
    alone can't catch this, since it doesn't know FILE's columns."""

    @pytest.mark.parametrize(
        ("has_fuel", "input_energy_type", "expected_error"),
        [
            (True, EnergyType.FUEL_GAS, None),
            (True, EnergyType.ELECTRICAL, "FUEL column"),
            (True, EnergyType.MECHANICAL, "FUEL column"),
            (False, EnergyType.ELECTRICAL, None),
            (False, EnergyType.MECHANICAL, None),
            (False, EnergyType.FUEL_GAS, "POWER column"),
        ],
    )
    def test_input_energy_type_against_file_columns(self, has_fuel, input_energy_type, expected_error):
        if expected_error is None:
            validate_input_energy_type("compressor", has_fuel, input_energy_type)
        else:
            with pytest.raises(ValueError, match=expected_error):
                validate_input_energy_type("compressor", has_fuel, input_energy_type)


class TestExpandSampledCompressors:
    """expand_sampled_compressors picks the resolved unit type from FILE's columns and,
    when FILE has only POWER, from what INPUT itself provides."""

    def test_fuel_only_becomes_fuel_gas_consumer(self):
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {
                        "NAME": "compressor",
                        "TYPE": "SAMPLED_COMPRESSOR",
                        "INPUT": "fuel",
                        "FILE": "compressor.csv",
                        "RATE": 50000,
                    },
                ],
            }
        )
        original = network.units[0]
        resource = _resource(headers=["RATE", "FUEL"], data=[[1000, 100], [2000, 150]])
        expanded = expand_sampled_compressors(network, {"compressor.csv": resource})
        assert [type(unit) for unit in expanded.units] == [_SampledFuelGasConsumer]
        # _retag must carry over the unit's own already-validated fields unchanged.
        unit = typing.cast(_SampledFuelGasConsumer, expanded.units[0])
        assert unit.name == "compressor"
        assert unit.input == "fuel"
        assert unit.file == "compressor.csv"
        assert unit.rate == 50000
        assert unit.suction_pressure is None
        assert unit.discharge_pressure is None
        assert unit.model_fields_set == original.model_fields_set

    def test_power_only_with_electrical_input_becomes_electrical_consumer(self):
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE"}],
                "UNITS": [
                    {
                        "NAME": "compressor",
                        "TYPE": "SAMPLED_COMPRESSOR",
                        "INPUT": "grid",
                        "FILE": "compressor.csv",
                        "RATE": 50000,
                    },
                ],
            }
        )
        resource = _resource(headers=["RATE", "POWER"], data=[[1000, 1.0], [2000, 1.5]])
        expanded = expand_sampled_compressors(network, {"compressor.csv": resource})
        assert [type(unit) for unit in expanded.units] == [_SampledElectricalConsumer]

    def test_power_only_with_mechanical_input_becomes_mechanical_consumer(self):
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel"},
                    {
                        "NAME": "compressor",
                        "TYPE": "SAMPLED_COMPRESSOR",
                        "INPUT": "turbine",
                        "FILE": "compressor.csv",
                        "RATE": 50000,
                    },
                ],
            }
        )
        resource = _resource(headers=["RATE", "POWER"], data=[[1000, 1.0], [2000, 1.5]])
        expanded = expand_sampled_compressors(network, {"compressor.csv": resource})
        # The explicitly modelled GAS_TURBINE is passed through untouched, in place.
        assert [type(unit) for unit in expanded.units] == [YamlGasTurbine, _SampledMechanicalConsumer]
        assert [unit.name for unit in expanded.units] == ["turbine", "compressor"]
        assert expanded.units[0] is network.units[0]

    def test_unresolvable_input_raises(self):
        """Defensive invariant guard, not a user-facing scenario: YamlEnergyNetwork
        validation only accepts an INPUT naming a source or a unit with a known output
        energy type, and SAMPLED_COMPRESSOR itself can never be another unit's INPUT (it
        is in CONSUMER_TYPES), so INPUT's energy type is always statically resolvable.
        Reaching this guard means that invariant has been broken; the private helper is
        called directly here since the public entry point cannot construct the case."""
        unit = YamlSampledCompressor.model_validate(
            {
                "NAME": "compressor",
                "TYPE": "SAMPLED_COMPRESSOR",
                "INPUT": "unresolvable",
                "FILE": "compressor.csv",
                "RATE": 50000,
            }
        )
        resource = _resource(headers=["RATE", "POWER"], data=[[1000, 1.0], [2000, 1.5]])
        with pytest.raises(IllegalStateException, match="cannot determine the energy type provided by INPUT"):
            _expand_sampled_compressor(unit, {"compressor.csv": resource}, output_type_by_name={}, all_names=set())

    def test_fuel_and_power_splits_into_turbine_and_mechanical_consumer(self):
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {
                        "NAME": "compressor",
                        "TYPE": "SAMPLED_COMPRESSOR",
                        "INPUT": "fuel",
                        "FILE": "compressor.csv",
                        "RATE": 50000,
                    },
                ],
            }
        )
        resource = _resource(
            headers=["RATE", "FUEL", "POWER"],
            data=[[1000, 100, 1.0], [2000, 150, 1.5], [3000, 200, 2.0]],
        )
        expanded = expand_sampled_compressors(network, {"compressor.csv": resource})
        assert [type(unit) for unit in expanded.units] == [_SampledGasTurbine, _SampledMechanicalConsumer]
        turbine = typing.cast(_SampledGasTurbine, expanded.units[0])
        compressor = typing.cast(_SampledMechanicalConsumer, expanded.units[1])
        # The turbine takes over the original unit's declared INPUT and FILE; the
        # mechanical consumer's INPUT is rewired to the (freshly generated) turbine.
        assert turbine.input == "fuel"
        assert turbine.file == "compressor.csv"
        assert compressor.input == turbine.name
        assert compressor.file == "compressor.csv"
        assert compressor.name == "compressor"

    def test_missing_file_raises_value_error(self):
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {
                        "NAME": "compressor",
                        "TYPE": "SAMPLED_COMPRESSOR",
                        "INPUT": "fuel",
                        "FILE": "missing.csv",
                        "RATE": 50000,
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="cannot resolve FILE 'missing.csv'"):
            expand_sampled_compressors(network, {})

    def test_fuel_and_power_with_non_invertible_samples_raises(self):
        """FUEL+POWER implies a synthetic turbine (power -> fuel), which requires fuel
        and power to be strictly monotonic - two different fuel values at the same
        power breaks that. expand_sampled_compressors itself only inspects FILE's
        column topology (cheap) and doesn't build the model, so this is only caught
        once the model is actually built, e.g. by build_sampled_compressor_model."""
        resource = _resource(
            headers=["RATE", "FUEL", "POWER"],
            data=[[1000, 100, 1.0], [2000, 150, 1.0], [3000, 120, 1.0]],
        )
        with pytest.raises(IllegalStateException, match="strictly monotonic"):
            build_sampled_compressor_model(resource)

    def test_input_energy_type_mismatching_file_raises(self):
        """The INPUT/FILE cross-check must be reached from the public entry point, not
        only from validate_input_energy_type called directly."""
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE"}],
                "UNITS": [
                    {
                        "NAME": "compressor",
                        "TYPE": "SAMPLED_COMPRESSOR",
                        "INPUT": "grid",
                        "FILE": "compressor.csv",
                        "RATE": 50000,
                    },
                ],
            }
        )
        resource = _resource(headers=["RATE", "FUEL"], data=[[1000, 100], [2000, 150]])
        with pytest.raises(ValueError, match="'compressor': INPUT provides ELECTRICAL, but FILE has a FUEL column"):
            expand_sampled_compressors(network, {"compressor.csv": resource})

    def test_network_without_sampled_compressors_is_unchanged(self):
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "fuel"},
                    {"NAME": "load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "genset", "LOAD": 5},
                    {"NAME": "flare", "TYPE": "FUEL_GAS_CONSUMER", "INPUT": "fuel", "RATE": 1200},
                ],
            }
        )

        expanded = expand_sampled_compressors(network, {})

        assert [unit is original for unit, original in zip(expanded.units, network.units, strict=True)] == [True] * 3
        assert [unit.name for unit in expanded.units] == ["genset", "load", "flare"]
        assert expanded.sources == network.sources

    def test_two_fuel_and_power_compressors_get_distinct_turbine_names(self):
        """EnergyNetworkMapper keys its node lookup by name, so two independently expanded
        compressors must not end up sharing a generated turbine name."""
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {
                        "NAME": "compressor_a",
                        "TYPE": "SAMPLED_COMPRESSOR",
                        "INPUT": "fuel",
                        "FILE": "compressor.csv",
                        "RATE": 50000,
                    },
                    {
                        "NAME": "compressor_b",
                        "TYPE": "SAMPLED_COMPRESSOR",
                        "INPUT": "fuel",
                        "FILE": "compressor.csv",
                        "RATE": 60000,
                    },
                ],
            }
        )
        resource = _resource(
            headers=["RATE", "FUEL", "POWER"],
            data=[[1000, 100, 1.0], [2000, 150, 1.5], [3000, 200, 2.0]],
        )

        expanded = expand_sampled_compressors(network, {"compressor.csv": resource})

        assert [type(unit) for unit in expanded.units] == [
            _SampledGasTurbine,
            _SampledMechanicalConsumer,
            _SampledGasTurbine,
            _SampledMechanicalConsumer,
        ]
        names = [unit.name for unit in expanded.units]
        assert len(set(names)) == 4
        assert expanded.units[0].name != expanded.units[2].name
        assert expanded.units[1].input == expanded.units[0].name
        assert expanded.units[3].input == expanded.units[2].name
        assert [expanded.units[1].name, expanded.units[3].name] == ["compressor_a", "compressor_b"]

    def test_turbine_name_colliding_with_an_existing_consumer_raises(self):
        """The generated turbine name must be checked against every existing name in the
        network, not just sources/output-producing units - a plain consumer can already
        be sitting on the name a split would otherwise silently generate and collide
        with (regression: output_type_by_name only contains output-producing units)."""
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {
                        "NAME": "compressor",
                        "TYPE": "SAMPLED_COMPRESSOR",
                        "INPUT": "fuel",
                        "FILE": "compressor.csv",
                        "RATE": 50000,
                    },
                    {
                        "NAME": "compressor-turbine",
                        "TYPE": "FUEL_GAS_CONSUMER",
                        "INPUT": "fuel",
                        "RATE": 10,
                    },
                ],
            }
        )
        resource = _resource(
            headers=["RATE", "FUEL", "POWER"],
            data=[[1000, 100, 1.0], [2000, 150, 1.5], [3000, 200, 2.0]],
        )

        with pytest.raises(ValueError, match="'compressor-turbine' is already in use"):
            expand_sampled_compressors(network, {"compressor.csv": resource})


class TestSampledSubclassesUnreachableFromYaml:
    """The whole safety argument for _retag/expand_sampled_compressors depends on these
    subclasses never being reachable from the YamlComponent discriminated union -
    otherwise a user could smuggle one in directly via YAML. This pins that invariant
    down as a test instead of leaving it as a docstring claim."""

    def test_parsing_a_sampled_compressor_unit_never_yields_a_subclass(self):
        """Beyond not being union members, the subclasses share YamlSampledCompressor's
        exact 'SAMPLED_COMPRESSOR' discriminator, so there's no TYPE value a user could
        write to make pydantic resolve to one - parsing always yields the exact base
        class."""
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {
                        "NAME": "compressor",
                        "TYPE": "SAMPLED_COMPRESSOR",
                        "INPUT": "fuel",
                        "FILE": "compressor.csv",
                        "RATE": 50000,
                    },
                ],
            }
        )
        assert type(network.units[0]) is YamlSampledCompressor
