from pathlib import Path

import pytest
import yaml
from pydantic import TypeAdapter, ValidationError

from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlComponent,
    YamlCompressorSampled,
    YamlElectricalBus,
    YamlElectricalCable,
    YamlElectricalConsumer,
    YamlEnergyNetwork,
    YamlEnergySource,
    YamlFuelGasConsumer,
    YamlFuelGasManifold,
    YamlGeneratorSet,
    YamlMechanicalConsumer,
)

EXAMPLE_YAML = Path(__file__).parents[3] / "src" / "libecalc" / "examples" / "energy" / "energy_network.yaml"

_component_adapter = TypeAdapter(YamlComponent)


def _load_network(yaml_path: Path) -> YamlEnergyNetwork:
    raw = yaml.safe_load(yaml_path.read_text())
    return YamlEnergyNetwork.model_validate(raw["ENERGY_NETWORK"])


class TestExampleYamlParsing:
    def test_parses_example_yaml(self):
        network = _load_network(EXAMPLE_YAML)
        assert len(network.sources) == 5
        assert len(network.units) == 14

    def test_sources_have_no_input(self):
        network = _load_network(EXAMPLE_YAML)
        by_name = {s.name: s for s in network.sources}
        assert by_name["fuel_gas"].type == "FUEL_GAS_SOURCE"
        assert by_name["power_from_shore"].type == "ELECTRICAL_SOURCE"
        assert by_name["power_from_shore"].capacity == 20

    def test_units_are_correct_types(self):
        network = _load_network(EXAMPLE_YAML)
        by_name = {c.name: c for c in network.units}

        assert isinstance(by_name["genset_a"], YamlGeneratorSet)
        assert isinstance(by_name["electrical_bus"], YamlElectricalBus)
        assert isinstance(by_name["subsea_cable"], YamlElectricalCable)
        assert isinstance(by_name["base_load"], YamlElectricalConsumer)
        assert isinstance(by_name["flare"], YamlFuelGasConsumer)
        assert isinstance(by_name["export_train"], YamlMechanicalConsumer)
        assert isinstance(by_name["gas_compressor_sampled"], YamlCompressorSampled)

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
        assert isinstance(bus, YamlElectricalBus)
        assert bus.dispatch_strategy == "PRIORITY"
        assert [(junction_input.name, junction_input.capacity) for junction_input in bus.get_inputs()] == [
            ("subsea_cable", 19.4),
            ("wind_turbine", 4.4),
        ]


class TestNumericBounds:
    def test_negative_capacity_on_source_rejected(self):
        with pytest.raises(ValidationError, match="CAPACITY must be non-negative"):
            YamlEnergySource.model_validate({"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE", "CAPACITY": -10})

    def test_negative_capacity_on_converter_rejected(self):
        with pytest.raises(ValidationError, match="CAPACITY must be non-negative"):
            _component_adapter.validate_python({"NAME": "g", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "CAPACITY": -5})

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
            {"NAME": "g", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "CAPACITY": "$var.rate"}
        )
        assert comp.capacity == "$var.rate"


class TestJunctionValidation:
    def test_dispatch_strategy_required(self):
        with pytest.raises(ValidationError, match=r"DISPATCH_STRATEGY\n\s+Field required"):
            _component_adapter.validate_python({"NAME": "bus", "TYPE": "ELECTRICAL_BUS", "INPUT": ["a", "b"]})

    def test_single_input_junction_rejected(self):
        with pytest.raises(ValidationError, match="at least 2 items"):
            _component_adapter.validate_python(
                {"NAME": "bus", "TYPE": "ELECTRICAL_BUS", "INPUT": ["a"], "DISPATCH_STRATEGY": "PRIORITY"}
            )

    def test_duplicate_input_refs_rejected(self):
        with pytest.raises(ValidationError, match="duplicate INPUT"):
            _component_adapter.validate_python(
                {"NAME": "bus", "TYPE": "ELECTRICAL_BUS", "INPUT": ["a", "a"], "DISPATCH_STRATEGY": "PRIORITY"}
            )


class TestJunctionInputs:
    def test_mixed_entries_keep_declared_order(self):
        manifold = _component_adapter.validate_python(
            {
                "NAME": "manifold",
                "TYPE": "FUEL_GAS_MANIFOLD",
                "INPUT": ["c", {"NAME": "a", "CAPACITY": "$var.limit"}, {"NAME": "b"}],
                "DISPATCH_STRATEGY": "PRIORITY",
            }
        )
        assert isinstance(manifold, YamlFuelGasManifold)
        assert [(junction_input.name, junction_input.capacity) for junction_input in manifold.get_inputs()] == [
            ("c", None),
            ("a", "$var.limit"),
            ("b", None),
        ]

    def test_equal_split_rejected_until_implemented(self):
        with pytest.raises(ValidationError, match="EQUAL_SPLIT is not supported yet"):
            _component_adapter.validate_python(
                {"NAME": "bus", "TYPE": "ELECTRICAL_BUS", "INPUT": ["a", "b"], "DISPATCH_STRATEGY": "EQUAL_SPLIT"}
            )

    def test_negative_input_capacity_rejected(self):
        with pytest.raises(ValidationError, match="CAPACITY must be non-negative"):
            _component_adapter.validate_python(
                {
                    "NAME": "bus",
                    "TYPE": "ELECTRICAL_BUS",
                    "INPUT": [{"NAME": "a", "CAPACITY": -1}, "b"],
                    "DISPATCH_STRATEGY": "PRIORITY",
                }
            )

    def test_duplicate_across_name_and_object_entries_rejected(self):
        with pytest.raises(ValidationError, match="duplicate INPUT"):
            _component_adapter.validate_python(
                {
                    "NAME": "bus",
                    "TYPE": "ELECTRICAL_BUS",
                    "INPUT": ["a", {"NAME": "a", "CAPACITY": 5}],
                    "DISPATCH_STRATEGY": "PRIORITY",
                }
            )

    def test_unknown_object_input_rejected(self):
        with pytest.raises(ValueError, match="not a known source or provider"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE"}],
                    "UNITS": [
                        {
                            "NAME": "bus",
                            "TYPE": "ELECTRICAL_BUS",
                            "INPUT": ["grid", {"NAME": "missing", "CAPACITY": 5}],
                            "DISPATCH_STRATEGY": "PRIORITY",
                        },
                    ],
                }
            )

    def test_object_input_energy_type_mismatch_rejected(self):
        with pytest.raises(ValueError, match="expects ELECTRICAL input.*provides FUEL_GAS"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [
                        {"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE"},
                        {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"},
                    ],
                    "UNITS": [
                        {
                            "NAME": "bus",
                            "TYPE": "ELECTRICAL_BUS",
                            "INPUT": ["grid", {"NAME": "fuel", "CAPACITY": 5}],
                            "DISPATCH_STRATEGY": "PRIORITY",
                        }
                    ],
                }
            )

    def test_object_input_cycle_rejected(self):
        with pytest.raises(ValueError, match="Cycle detected"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE"}],
                    "UNITS": [
                        {
                            "NAME": "first_bus",
                            "TYPE": "ELECTRICAL_BUS",
                            "INPUT": ["grid", {"NAME": "second_bus", "CAPACITY": 5}],
                            "DISPATCH_STRATEGY": "PRIORITY",
                        },
                        {
                            "NAME": "second_bus",
                            "TYPE": "ELECTRICAL_BUS",
                            "INPUT": ["grid", {"NAME": "first_bus"}],
                            "DISPATCH_STRATEGY": "PRIORITY",
                        },
                    ],
                }
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
                    "UNITS": [{"NAME": "fuel", "TYPE": "GENERATOR_SET", "INPUT": "fuel"}],
                }
            )

    def test_invalid_input_reference_rejected(self):
        with pytest.raises(ValueError, match="not a known source or provider"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "nonexistent"},
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
                        {"NAME": "a", "TYPE": "GENERATOR_SET", "INPUT": "b"},
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
                        {"NAME": "a", "TYPE": "GENERATOR_SET", "INPUT": "a"},
                    ],
                }
            )

    def test_incompatible_energy_type_rejected(self):
        with pytest.raises(ValueError, match="expects FUEL_GAS input.*provides ELECTRICAL"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE", "CAPACITY": 10}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "grid"},
                    ],
                }
            )

    def test_consumer_energy_type_mismatch_rejected(self):
        with pytest.raises(ValueError, match="expects ELECTRICAL input.*provides MECHANICAL"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel"},
                        {"NAME": "load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "turbine", "LOAD": 5},
                    ],
                }
            )

    def test_diesel_genset_rejected(self):
        with pytest.raises(ValueError, match="expects FUEL_GAS input"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "diesel", "TYPE": "DIESEL_SOURCE"}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "diesel"},
                    ],
                }
            )

    def test_compatible_chain_accepted(self):
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "fuel"},
                    {"NAME": "motor", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "genset"},
                    {
                        "NAME": "compressor",
                        "TYPE": "MECHANICAL_CONSUMER",
                        "INPUT": "motor",
                        "PROCESS_SIMULATION": "sim",
                    },
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
                        {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel"},
                        {"NAME": "comp", "TYPE": "MECHANICAL_CONSUMER", "INPUT": "turbine"},
                    ],
                }
            )

    def test_mechanical_consumer_rejects_both_load_and_sim(self):
        with pytest.raises(ValueError, match="cannot specify both"):
            _component_adapter.validate_python(
                {"NAME": "c", "TYPE": "MECHANICAL_CONSUMER", "INPUT": "x", "LOAD": 5, "PROCESS_SIMULATION": "sim"}
            )


class TestSampledCompressor:
    def test_parses_with_file_and_lookup_variables(self):
        comp = _component_adapter.validate_python(
            {"NAME": "c", "TYPE": "COMPRESSOR_SAMPLED", "INPUT": "fuel", "FILE": "c.csv", "RATE": 1000}
        )
        assert isinstance(comp, YamlCompressorSampled)
        assert comp.file == "c.csv"
        assert comp.rate == 1000

    def test_input_energy_type_is_not_checked_by_schema(self):
        for source_type in ("FUEL_GAS_SOURCE", "ELECTRICAL_SOURCE"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "src", "TYPE": source_type}],
                    "UNITS": [
                        {"NAME": "c", "TYPE": "COMPRESSOR_SAMPLED", "INPUT": "src", "FILE": "c.csv", "RATE": 1000}
                    ],
                }
            )

    def test_cannot_be_an_input(self):
        with pytest.raises(ValueError, match="not a known source or provider"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "c", "TYPE": "COMPRESSOR_SAMPLED", "INPUT": "fuel", "FILE": "c.csv", "RATE": 1000},
                        {"NAME": "load", "TYPE": "FUEL_GAS_CONSUMER", "INPUT": "c", "RATE": 5},
                    ],
                }
            )
