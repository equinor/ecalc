import pytest

from libecalc.presentation.yaml.mappers.energy.sampled_compressor_mapper import expand_sampled_compressors
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlEnergyNetwork,
    YamlEnergySource,
    YamlEnergySourceType,
    YamlFuelGasManifold,
    YamlGasTurbine,
    YamlSampledCompressor,
    _SampledElectricalConsumer,
    _SampledFuelGasConsumer,
    _SampledGasTurbine,
    _SampledMechanicalConsumer,
)

_FUEL_ONLY = MemoryResource(headers=["RATE", "FUEL"], data=[[0.0, 100.0], [1000.0, 2000.0]])
_POWER_ONLY = MemoryResource(headers=["RATE", "POWER"], data=[[0.0, 100.0], [1.0, 2.0]])
_FUEL_AND_POWER = MemoryResource(headers=["RATE", "FUEL", "POWER"], data=[[0.0, 100.0], [1000.0, 2000.0], [1.0, 2.0]])


def _network(*units: YamlSampledCompressor) -> YamlEnergyNetwork:
    return YamlEnergyNetwork(
        sources=[
            YamlEnergySource(name="fuel_gas", type=YamlEnergySourceType.FUEL_GAS_SOURCE),
            YamlEnergySource(name="power_from_shore", type=YamlEnergySourceType.ELECTRICAL_SOURCE),
        ],
        units=[
            YamlFuelGasManifold(name="fuel_manifold", type="FUEL_GAS_MANIFOLD", input=["fuel_gas"]),
            *units,
        ],
    )


def _compressor(name: str, input: str, file: str = "compressor.csv", rate: float = 50000) -> YamlSampledCompressor:
    return YamlSampledCompressor(name=name, type="SAMPLED_COMPRESSOR", input=input, file=file, rate=rate)


class TestExpandSampledCompressors:
    def test_fuel_only_becomes_fuel_gas_consumer(self):
        network = _network(_compressor("compressor", input="fuel_manifold"))
        expanded = expand_sampled_compressors(network, {"compressor.csv": _FUEL_ONLY})

        [unit] = [u for u in expanded.units if u.name == "compressor"]
        assert type(unit) is _SampledFuelGasConsumer
        assert unit.input == "fuel_manifold"

    def test_power_only_with_electrical_input_becomes_electrical_consumer(self):
        network = _network(_compressor("compressor", input="power_from_shore"))
        expanded = expand_sampled_compressors(network, {"compressor.csv": _POWER_ONLY})

        [unit] = [u for u in expanded.units if u.name == "compressor"]
        assert type(unit) is _SampledElectricalConsumer

    def test_power_only_with_mechanical_input_becomes_mechanical_consumer(self):
        network = _network(
            YamlGasTurbine(name="turbine", type="GAS_TURBINE", input="fuel_manifold"),
            _compressor("compressor", input="turbine"),
        )
        expanded = expand_sampled_compressors(network, {"compressor.csv": _POWER_ONLY})

        [unit] = [u for u in expanded.units if u.name == "compressor"]
        assert type(unit) is _SampledMechanicalConsumer

    def test_fuel_and_power_splits_into_turbine_and_compressor(self):
        network = _network(_compressor("compressor", input="fuel_manifold"))
        expanded = expand_sampled_compressors(network, {"compressor.csv": _FUEL_AND_POWER})

        by_name = {u.name: u for u in expanded.units}
        assert type(by_name["compressor-turbine"]) is _SampledGasTurbine
        assert by_name["compressor-turbine"].input == "fuel_manifold"
        assert type(by_name["compressor"]) is _SampledMechanicalConsumer
        assert by_name["compressor"].input == "compressor-turbine"

    def test_turbine_name_collision_raises(self):
        network = _network(
            _compressor("compressor", input="fuel_manifold"),
            _compressor("compressor-turbine", input="fuel_manifold"),
        )
        with pytest.raises(ValueError, match="already in use"):
            expand_sampled_compressors(
                network, {"compressor.csv": _FUEL_AND_POWER, "compressor-turbine.csv": _FUEL_ONLY}
            )

    def test_wrong_input_energy_type_raises(self):
        network = _network(_compressor("compressor", input="power_from_shore"))
        with pytest.raises(ValueError, match="FUEL_GAS"):
            expand_sampled_compressors(network, {"compressor.csv": _FUEL_ONLY})

    def test_leaves_non_sampled_units_untouched(self):
        network = _network()
        expanded = expand_sampled_compressors(network, {})

        assert [u.name for u in expanded.units] == [u.name for u in network.units]
