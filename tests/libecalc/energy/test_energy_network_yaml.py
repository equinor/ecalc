from pathlib import Path

import pytest
import yaml
from pydantic import TypeAdapter, ValidationError

from libecalc.energy.energy_use import EnergyUse
from libecalc.presentation.yaml.yaml_types.energy.yaml_consumers import (
    YamlCompressor,
    YamlElectricalConsumer,
    YamlFuelGasConsumer,
    YamlPump,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_converters import YamlGeneratorSet
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlEnergyNetwork,
    YamlEnergyNetworkUnit,
    YamlEnergySource,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_junctions import YamlElectricalBus, YamlFuelGasManifold
from libecalc.presentation.yaml.yaml_types.energy.yaml_sources import (
    YamlDieselSource,
    YamlFuelGasSource,
    YamlOffshoreWind,
    YamlOnshoreGrid,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_transporters import YamlElectricalCable

EXAMPLE_YAML = Path(__file__).parents[3] / "src" / "libecalc" / "examples" / "energy" / "energy_network.yaml"

_component_adapter = TypeAdapter(YamlEnergyNetworkUnit)
_source_adapter = TypeAdapter(YamlEnergySource)


def _load_network(yaml_path: Path) -> YamlEnergyNetwork:
    raw = yaml.safe_load(yaml_path.read_text())
    return YamlEnergyNetwork.model_validate(raw["ENERGY_NETWORK"])


class TestExampleYamlParsing:
    def test_parses_example_yaml(self):
        network = _load_network(EXAMPLE_YAML)
        assert len(network.sources) == 5
        assert len(network.units) == 15

    def test_sources_are_correct_types(self):
        network = _load_network(EXAMPLE_YAML)
        by_name = {s.name: s for s in network.sources}
        assert isinstance(by_name["fuel_gas"], YamlFuelGasSource)
        assert isinstance(by_name["diesel"], YamlDieselSource)
        assert isinstance(by_name["power_from_shore"], YamlOnshoreGrid)
        assert isinstance(by_name["wind_turbine"], YamlOffshoreWind)

    def test_units_are_correct_types(self):
        network = _load_network(EXAMPLE_YAML)
        by_name = {c.name: c for c in network.units}

        assert isinstance(by_name["genset_a"], YamlGeneratorSet)
        assert isinstance(by_name["electrical_bus"], YamlElectricalBus)
        assert isinstance(by_name["fuel_manifold"], YamlFuelGasManifold)
        assert isinstance(by_name["subsea_cable"], YamlElectricalCable)
        assert isinstance(by_name["base_load"], YamlElectricalConsumer)
        assert isinstance(by_name["flare"], YamlFuelGasConsumer)
        assert isinstance(by_name["export_train"], YamlCompressor)
        assert isinstance(by_name["waterinj_train"], YamlPump)

    def test_consumers_use_load_and_rate(self):
        network = _load_network(EXAMPLE_YAML)
        by_name = {c.name: c for c in network.units}

        assert by_name["base_load"].load == 5
        assert by_name["flare"].rate == 1200
        assert by_name["diesel_consumers"].rate == 500
        assert by_name["export_train"].process_simulation == "export_compressor_sim"

    def test_dispatch_strategy_on_junction(self):
        network = _load_network(EXAMPLE_YAML)
        bus = next(c for c in network.units if c.name == "electrical_bus")
        assert bus.dispatch_strategy == "PRIORITY"

    def test_consumers_have_energy_use_metadata(self):
        network = _load_network(EXAMPLE_YAML)
        by_name = {unit.name: unit for unit in network.units}

        base_load = by_name["base_load"]
        assert base_load.metadata is not None
        assert base_load.metadata.energy_use == EnergyUse.BASE_LOAD

        flare = by_name["flare"]
        assert flare.metadata is not None
        assert flare.metadata.energy_use == EnergyUse.FLARING


class TestNumericBounds:
    def test_negative_capacity_on_source_rejected(self):
        with pytest.raises(ValidationError, match="CAPACITY must be non-negative"):
            _source_adapter.validate_python({"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE", "CAPACITY": -10})

    def test_negative_capacity_on_converter_rejected(self):
        with pytest.raises(ValidationError, match="CAPACITY must be non-negative"):
            _component_adapter.validate_python(
                {"NAME": "g", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "CAPACITY": -5, "MODEL": "model"}
            )

    def test_efficiency_zero_rejected(self):
        with pytest.raises(ValidationError, match="EFFICIENCY must be in"):
            _component_adapter.validate_python({"NAME": "m", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "g", "EFFICIENCY": 0})

    def test_efficiency_above_one_rejected(self):
        with pytest.raises(ValidationError, match="EFFICIENCY must be in"):
            _component_adapter.validate_python(
                {"NAME": "m", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "g", "EFFICIENCY": 1.5}
            )

    def test_efficiency_one_accepted(self):
        comp = _component_adapter.validate_python(
            {"NAME": "c", "TYPE": "ELECTRICAL_CABLE", "INPUT": "g", "EFFICIENCY": 1}
        )
        assert comp.efficiency == 1

    def test_negative_load_rejected(self):
        with pytest.raises(ValidationError, match="LOAD must be non-negative"):
            _component_adapter.validate_python({"NAME": "c", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "g", "LOAD": -1})

    def test_negative_rate_rejected(self):
        with pytest.raises(ValidationError, match="RATE must be non-negative"):
            _component_adapter.validate_python({"NAME": "c", "TYPE": "FUEL_GAS_CONSUMER", "INPUT": "f", "RATE": -100})

    def test_expression_capacity_accepted(self):
        """String expressions bypass numeric bounds — validated at evaluation time."""
        comp = _component_adapter.validate_python(
            {"NAME": "g", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "CAPACITY": "$var.rate", "MODEL": "generator_model"}
        )
        assert comp.capacity == "$var.rate"


class TestJunctionValidation:
    def test_dispatch_strategy_required_for_multi_input(self):
        with pytest.raises(ValidationError, match="DISPATCH_STRATEGY is required"):
            _component_adapter.validate_python({"NAME": "bus", "TYPE": "ELECTRICAL_BUS", "INPUT": ["a", "b"]})

    def test_single_input_junction_ok_without_strategy(self):
        comp = _component_adapter.validate_python({"NAME": "bus", "TYPE": "ELECTRICAL_BUS", "INPUT": ["a"]})
        assert comp.dispatch_strategy is None

    def test_duplicate_input_refs_rejected(self):
        with pytest.raises(ValidationError, match="duplicate INPUT"):
            _component_adapter.validate_python(
                {"NAME": "bus", "TYPE": "ELECTRICAL_BUS", "INPUT": ["a", "a"], "DISPATCH_STRATEGY": "PRIORITY"}
            )


class TestNetworkValidation:
    def test_duplicate_names_rejected(self):
        with pytest.raises(ValueError, match="Duplicate"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [
                        {"NAME": "dup", "TYPE": "FUEL_GAS_SOURCE"},
                        {"NAME": "dup", "TYPE": "FUEL_GAS_SOURCE"},
                    ],
                }
            )

    def test_duplicate_name_across_source_and_component(self):
        with pytest.raises(ValueError, match="Duplicate"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [{"NAME": "fuel", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "MODEL": "model"}],
                }
            )

    def test_invalid_input_reference_rejected(self):
        with pytest.raises(ValueError, match="not a known source or provider"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "nonexistent", "MODEL": "model"},
                    ],
                }
            )

    def test_consumer_referencing_consumer_rejected(self):
        with pytest.raises(ValueError, match="not a known source or provider"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "load_a", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "fuel", "LOAD": 5},
                        {"NAME": "load_b", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "load_a", "LOAD": 3},
                    ],
                }
            )

    def test_cycle_rejected(self):
        with pytest.raises(ValueError, match="Cycle detected"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "a", "TYPE": "GENERATOR_SET", "INPUT": "b", "MODEL": "model"},
                        {"NAME": "b", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "a"},
                    ],
                }
            )

    def test_self_reference_rejected(self):
        with pytest.raises(ValueError, match="Cycle detected"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "a", "TYPE": "GENERATOR_SET", "INPUT": "a", "MODEL": "model"},
                    ],
                }
            )

    def test_incompatible_energy_type_rejected(self):
        with pytest.raises(ValueError, match="expects FUEL_GAS input.*provides ELECTRICAL"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "grid", "TYPE": "ONSHORE_GRID", "CAPACITY": 10}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "grid", "MODEL": "model"},
                    ],
                }
            )

    def test_consumer_energy_type_mismatch_rejected(self):
        with pytest.raises(ValueError, match="expects ELECTRICAL input.*provides MECHANICAL"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel", "MODEL": "model"},
                        {"NAME": "load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "turbine", "LOAD": 5},
                    ],
                }
            )

    def test_diesel_genset_rejected(self):
        with pytest.raises(
            ValueError,
            match="expects FUEL_GAS input.*provides DIESEL",
        ):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "diesel", "TYPE": "DIESEL_SOURCE"}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "diesel", "MODEL": "model"},
                    ],
                }
            )

    def test_compatible_chain_accepted(self):
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "MODEL": "model"},
                    {"NAME": "motor", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "genset"},
                    {"NAME": "compressor", "TYPE": "COMPRESSOR", "INPUT": "motor", "PROCESS_SIMULATION": "sim"},
                ],
            }
        )
        assert len(network.units) == 3

    def test_mechanical_consumer_needs_load_or_sim(self):
        with pytest.raises(ValueError, match="either LOAD or PROCESS_SIMULATION"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel", "MODEL": "model"},
                        {"NAME": "comp", "TYPE": "COMPRESSOR", "INPUT": "turbine"},
                    ],
                }
            )

    def test_compressor_rejects_both_load_and_sim(self):
        with pytest.raises(ValueError, match="cannot specify both"):
            _component_adapter.validate_python(
                {"NAME": "c", "TYPE": "COMPRESSOR", "INPUT": "x", "LOAD": 5, "PROCESS_SIMULATION": "sim"}
            )


class TestSchemaValidation:
    def test_source_with_input_rejected(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            _source_adapter.validate_python(
                {
                    "NAME": "fuel",
                    "TYPE": "FUEL_GAS_SOURCE",
                    "INPUT": "other",
                }
            )
