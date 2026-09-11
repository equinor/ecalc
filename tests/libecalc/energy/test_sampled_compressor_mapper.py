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
    YamlComponent,
    YamlEnergyNetwork,
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

    def test_power_model_accepts_mechanical_input(self):
        resource = _resource(headers=["RATE", "POWER"], data=[[1000, 1.0], [2000, 1.5]])
        model = build_sampled_compressor_model(resource)
        validate_input_energy_type("compressor", model, EnergyType.MECHANICAL)

    def test_power_model_rejects_fuel_gas_input(self):
        resource = _resource(headers=["RATE", "POWER"], data=[[1000, 1.0], [2000, 1.5]])
        model = build_sampled_compressor_model(resource)
        with pytest.raises(ValueError, match="POWER column"):
            validate_input_energy_type("compressor", model, EnergyType.FUEL_GAS)


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
        resource = _resource(headers=["RATE", "FUEL"], data=[[1000, 100], [2000, 150]])
        expanded = expand_sampled_compressors(network, {"compressor.csv": resource})
        assert [type(unit) for unit in expanded.units] == [_SampledFuelGasConsumer]
        # _retag must carry over the unit's own already-validated fields unchanged.
        unit = typing.cast(_SampledFuelGasConsumer, expanded.units[0])
        assert unit.name == "compressor"
        assert unit.input == "fuel"
        assert unit.file == "compressor.csv"

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
        units_by_name = {unit.name: unit for unit in expanded.units}
        assert type(units_by_name["compressor"]) is _SampledMechanicalConsumer

    def test_power_only_with_unresolvable_input_defaults_to_electrical(self):
        """If INPUT's energy type can't be determined statically, the legacy
        COMPRESSOR_TABULAR default (electrical/genset) applies. Note: this is
        currently unreachable via the public YAML schema (SAMPLED_COMPRESSOR is always
        a terminal consumer, so nothing can ever have it as INPUT, and every other
        provider type is a key in OUTPUT_ENERGY/SOURCE_OUTPUT_ENERGY) - this test
        exercises the defensive fallback directly via the private helper."""
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
        resolved = _expand_sampled_compressor(unit, {"compressor.csv": resource}, output_type_by_name={})
        assert [type(u) for u in resolved] == [_SampledElectricalConsumer]

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
        to be a well-defined (invertible) function of power - two different fuel
        values at the same power breaks that."""
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
            data=[[1000, 100, 1.0], [2000, 150, 1.0], [3000, 120, 1.0]],
        )
        with pytest.raises(IllegalStateException, match="strictly increasing"):
            expand_sampled_compressors(network, {"compressor.csv": resource})


class TestSampledSubclassesUnreachableFromYaml:
    """The whole safety argument for _retag/expand_sampled_compressors depends on these
    subclasses never being members of (or matched by) the YamlComponent discriminated
    union - otherwise a user could smuggle one in directly via YAML. This pins that
    invariant down as a test instead of leaving it as a docstring claim."""

    def test_subclasses_not_in_yaml_component_union(self):
        union_members = typing.get_args(typing.get_args(YamlComponent)[0])
        for cls in (
            _SampledFuelGasConsumer,
            _SampledElectricalConsumer,
            _SampledGasTurbine,
            _SampledMechanicalConsumer,
        ):
            assert cls not in union_members

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
