from pathlib import Path

import pytest
import yaml
from pydantic import TypeAdapter, ValidationError

from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlComponent,
    YamlCompressorSampled,
    YamlDriveTrain,
    YamlElectricalBus,
    YamlElectricalCable,
    YamlElectricalConsumer,
    YamlEnergyNetwork,
    YamlEnergySource,
    YamlFuelGasConsumer,
    YamlGasTurbine,
    YamlGeneratorSet,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineDefinition

EXAMPLE_YAML = Path(__file__).parents[3] / "src" / "libecalc" / "examples" / "energy" / "energy_network.yaml"

TURBINE = {"TYPE": "LOAD_TO_EFFICIENCY", "CURVE": {"LOAD": [5, 10], "EFFICIENCY": [0.2, 0.3]}}
GENERATOR_SET_MODEL = {"TYPE": "POWER_TO_FUEL", "CURVE": {"POWER": [5, 10], "FUEL": [20000, 35000]}}

_component_adapter = TypeAdapter(YamlComponent)
_energy_source_adapter = TypeAdapter(YamlEnergySource)


def _load_network(yaml_path: Path) -> YamlEnergyNetwork:
    raw = yaml.safe_load(yaml_path.read_text())
    return YamlEnergyNetwork.model_validate(raw["ENERGY_NETWORK"])


def _units_by_name(network: YamlEnergyNetwork) -> dict[str, YamlComponent]:
    return {c.name: c for c in network.units if not isinstance(c, YamlCompressorSampled | YamlDriveTrain)}


class TestExampleYamlParsing:
    def test_parses_example_yaml(self):
        network = _load_network(EXAMPLE_YAML)
        assert len(network.sources) == 5
        assert len(network.units) == 15
        turbine = next(unit for unit in network.units if isinstance(unit, YamlGasTurbine))
        assert isinstance(turbine.model, YamlTurbineDefinition)

    def test_sources_have_no_input(self):
        network = _load_network(EXAMPLE_YAML)
        by_name = {s.name: s for s in network.sources}
        assert by_name["fuel_gas"].type == "FUEL_GAS_SOURCE"
        assert by_name["power_from_shore"].type == "ELECTRICAL_SOURCE"
        assert by_name["power_from_shore"].capacity == 20

    def test_units_are_correct_types(self):
        network = _load_network(EXAMPLE_YAML)
        by_name = _units_by_name(network)

        assert isinstance(by_name["genset_a"], YamlGeneratorSet)
        assert isinstance(by_name["electrical_bus"], YamlElectricalBus)
        assert isinstance(by_name["subsea_cable"], YamlElectricalCable)
        assert isinstance(by_name["base_load"], YamlElectricalConsumer)
        assert isinstance(by_name["flare"], YamlFuelGasConsumer)
        assert isinstance(by_name["gas_compressor_turbine"], YamlGasTurbine)
        (drive_train,) = (unit for unit in network.units if isinstance(unit, YamlDriveTrain))
        assert drive_train.shaft == "export_shaft"
        (sampled_compressor,) = (unit for unit in network.units if isinstance(unit, YamlCompressorSampled))
        assert sampled_compressor.compressor == "23KA001 Gas Compressor"
        assert sampled_compressor.input == "gas_compressor_turbine"

    def test_consumers_use_load_and_rate(self):
        by_name = _units_by_name(_load_network(EXAMPLE_YAML))

        assert by_name["base_load"].load == 5
        assert by_name["flare"].rate == 1200
        assert by_name["diesel_consumers"].rate == 500

    def test_dispatch_strategy_on_junction(self):
        network = _load_network(EXAMPLE_YAML)
        bus = _units_by_name(network)["electrical_bus"]
        assert isinstance(bus, YamlElectricalBus)
        assert bus.dispatch_strategy == "PRIORITY"
        assert [(junction_input.name, junction_input.capacity) for junction_input in bus.get_inputs()] == [
            ("subsea_cable", 19.4),
            ("wind_turbine", 4.4),
        ]


class TestNumericBounds:
    def test_negative_capacity_on_source_rejected(self):
        with pytest.raises(ValidationError, match="CAPACITY must be non-negative"):
            _energy_source_adapter.validate_python({"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE", "CAPACITY": -10})

    def test_capacity_on_fuel_gas_source_rejected(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            _energy_source_adapter.validate_python({"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE", "CAPACITY": 10})

    def test_capacity_on_diesel_source_rejected(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            _energy_source_adapter.validate_python({"NAME": "diesel", "TYPE": "DIESEL_SOURCE", "CAPACITY": 10})

    def test_lower_heating_value_on_electrical_source_rejected(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            _energy_source_adapter.validate_python(
                {"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE", "LOWER_HEATING_VALUE": 38}
            )

    def test_zero_lower_heating_value_on_source_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            _energy_source_adapter.validate_python(
                {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE", "LOWER_HEATING_VALUE": 0}
            )

    def test_negative_capacity_on_converter_rejected(self):
        with pytest.raises(ValidationError, match="CAPACITY must be non-negative"):
            _component_adapter.validate_python({"NAME": "m", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "g", "CAPACITY": -5})

    def test_efficiency_zero_rejected(self):
        with pytest.raises(ValidationError, match="EFFICIENCY must be in"):
            _component_adapter.validate_python({"NAME": "m", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "g", "EFFICIENCY": 0})

    def test_efficiency_above_one_rejected(self):
        with pytest.raises(ValidationError, match="EFFICIENCY must be in"):
            _component_adapter.validate_python(
                {"NAME": "m", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "g", "EFFICIENCY": 1.5}
            )

    def test_mechanical_efficiency_given_in_percent_rejected(self):
        with pytest.raises(ValidationError, match="EFFICIENCY must be in"):
            _component_adapter.validate_python(
                {
                    "TYPE": "DRIVE_TRAIN",
                    "INPUT": "t",
                    "SHAFT": "s",
                    "MECHANICAL_EFFICIENCIES": [{"COMPRESSOR": "c", "EFFICIENCY": 95}],
                }
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
            {"NAME": "m", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "g", "CAPACITY": "$var.rate"}
        )
        assert comp.capacity == "$var.rate"


class TestLowerHeatingValueResolution:
    def test_gas_turbine_without_lower_heating_value_on_source_rejected(self):
        with pytest.raises(ValueError, match="could not resolve a LOWER_HEATING_VALUE"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [{"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel", "MODEL": TURBINE}],
                }
            )

    def test_diesel_engine_without_lower_heating_value_on_source_rejected(self):
        with pytest.raises(ValueError, match="could not resolve a LOWER_HEATING_VALUE"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "diesel", "TYPE": "DIESEL_SOURCE"}],
                    "UNITS": [{"NAME": "engine", "TYPE": "DIESEL_ENGINE", "INPUT": "diesel", "MODEL": TURBINE}],
                }
            )

    def test_generator_set_with_gas_turbine_model_without_lower_heating_value_rejected(self):
        with pytest.raises(ValueError, match="could not resolve a LOWER_HEATING_VALUE"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {
                            "NAME": "genset",
                            "TYPE": "GENERATOR_SET",
                            "INPUT": "fuel",
                            "MODEL": {"TYPE": "GAS_TURBINE_DRIVEN", "ENGINE": TURBINE, "GENERATOR_EFFICIENCY": 0.97},
                        }
                    ],
                }
            )

    def test_generator_set_requires_lower_heating_value_when_events_change_to_an_engine_model(self):
        """MODEL starts as a plain curve (no LHV needed), but CHANGES.CHANGE_TO switches to a GAS_TURBINE model
        partway through — the source must still have a LOWER_HEATING_VALUE, since the check must not only look
        at the initial MODEL.
        """
        with pytest.raises(ValueError, match="could not resolve a LOWER_HEATING_VALUE"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {
                            "NAME": "genset",
                            "TYPE": "GENERATOR_SET",
                            "INPUT": "fuel",
                            "MODEL": GENERATOR_SET_MODEL,
                            "CHANGES": [
                                {
                                    "REF": "upgrade",
                                    "CHANGE_TO": {
                                        "TYPE": "GAS_TURBINE_DRIVEN",
                                        "ENGINE": TURBINE,
                                        "GENERATOR_EFFICIENCY": 0.97,
                                    },
                                }
                            ],
                        }
                    ],
                }
            )


class TestGeneratorSetEnergyTypeCompatibility:
    def test_gas_turbine_generator_set_rejects_diesel_source(self):
        with pytest.raises(ValueError, match="expects FUEL_GAS input.*provides DIESEL"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "diesel", "TYPE": "DIESEL_SOURCE", "LOWER_HEATING_VALUE": 38.0}],
                    "UNITS": [
                        {
                            "NAME": "genset",
                            "TYPE": "GENERATOR_SET",
                            "INPUT": "diesel",
                            "MODEL": {"TYPE": "GAS_TURBINE_DRIVEN", "ENGINE": TURBINE, "GENERATOR_EFFICIENCY": 0.97},
                        }
                    ],
                }
            )

    def test_diesel_engine_generator_set_rejects_fuel_gas_source(self):
        with pytest.raises(ValueError, match="expects DIESEL input.*provides FUEL_GAS"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE", "LOWER_HEATING_VALUE": 38.0}],
                    "UNITS": [
                        {
                            "NAME": "genset",
                            "TYPE": "GENERATOR_SET",
                            "INPUT": "fuel",
                            "MODEL": {"TYPE": "DIESEL_ENGINE_DRIVEN", "ENGINE": TURBINE, "GENERATOR_EFFICIENCY": 0.97},
                        }
                    ],
                }
            )

    def test_curve_based_generator_set_accepts_either_fuel_or_diesel_source(self):
        for source_type, input_name in (("FUEL_GAS_SOURCE", "fuel"), ("DIESEL_SOURCE", "diesel")):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": input_name, "TYPE": source_type}],
                    "UNITS": [
                        {
                            "NAME": "genset",
                            "TYPE": "GENERATOR_SET",
                            "INPUT": input_name,
                            "MODEL": GENERATOR_SET_MODEL,
                        }
                    ],
                }
            )

    def test_generator_set_rejects_switching_between_incompatible_engine_types(self):
        with pytest.raises(ValueError, match="incompatible engine fuel types.*DIESEL.*FUEL_GAS"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE", "LOWER_HEATING_VALUE": 38.0}],
                    "UNITS": [
                        {
                            "NAME": "genset",
                            "TYPE": "GENERATOR_SET",
                            "INPUT": "fuel",
                            "MODEL": {"TYPE": "GAS_TURBINE_DRIVEN", "ENGINE": TURBINE, "GENERATOR_EFFICIENCY": 0.97},
                            "CHANGES": [
                                {
                                    "REF": "rebundle",
                                    "CHANGE_TO": {
                                        "TYPE": "DIESEL_ENGINE_DRIVEN",
                                        "ENGINE": TURBINE,
                                        "GENERATOR_EFFICIENCY": 0.97,
                                    },
                                }
                            ],
                        }
                    ],
                }
            )


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


class TestDriveTrainValidation:
    def test_compressor_listed_twice_in_mechanical_efficiencies_rejected(self):
        with pytest.raises(ValidationError, match="MECHANICAL_EFFICIENCIES lists compressors more than once: c"):
            _component_adapter.validate_python(
                {
                    "TYPE": "DRIVE_TRAIN",
                    "INPUT": "t",
                    "SHAFT": "s",
                    "MECHANICAL_EFFICIENCIES": [
                        {"COMPRESSOR": "c", "EFFICIENCY": 0.95},
                        {"COMPRESSOR": "c", "EFFICIENCY": 0.98},
                    ],
                }
            )


class TestJunctionInputs:
    def test_mixed_entries_keep_declared_order(self):
        bus = _component_adapter.validate_python(
            {
                "NAME": "bus",
                "TYPE": "ELECTRICAL_BUS",
                "INPUT": ["c", {"NAME": "a", "CAPACITY": "$var.limit"}, {"NAME": "b"}],
                "DISPATCH_STRATEGY": "PRIORITY",
            }
        )
        assert isinstance(bus, YamlElectricalBus)
        assert [(junction_input.name, junction_input.capacity) for junction_input in bus.get_inputs()] == [
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
                    "UNITS": [{"NAME": "fuel", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "MODEL": GENERATOR_SET_MODEL}],
                }
            )

    def test_invalid_input_reference_rejected(self):
        with pytest.raises(ValueError, match="not a known source or provider"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {
                            "NAME": "genset",
                            "TYPE": "GENERATOR_SET",
                            "INPUT": "nonexistent",
                            "MODEL": GENERATOR_SET_MODEL,
                        },
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
                        {"NAME": "a", "TYPE": "GENERATOR_SET", "INPUT": "b", "MODEL": GENERATOR_SET_MODEL},
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
                        {"NAME": "a", "TYPE": "GENERATOR_SET", "INPUT": "a", "MODEL": GENERATOR_SET_MODEL},
                    ],
                }
            )

    def test_incompatible_energy_type_rejected(self):
        with pytest.raises(ValueError, match=r"expects one of \['DIESEL', 'FUEL_GAS'\] input.*provides ELECTRICAL"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE", "CAPACITY": 10}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "grid", "MODEL": GENERATOR_SET_MODEL},
                    ],
                }
            )

    def test_consumer_energy_type_mismatch_rejected(self):
        with pytest.raises(ValueError, match="expects ELECTRICAL input.*provides MECHANICAL"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE", "LOWER_HEATING_VALUE": 38}],
                    "UNITS": [
                        {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel", "MODEL": TURBINE},
                        {"NAME": "load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "turbine", "LOAD": 5},
                    ],
                }
            )

    def test_diesel_genset_accepted(self):
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "diesel", "TYPE": "DIESEL_SOURCE"}],
                "UNITS": [
                    {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "diesel", "MODEL": GENERATOR_SET_MODEL},
                ],
            }
        )
        assert len(network.units) == 1

    def test_diesel_engine_rejects_fuel_gas_input(self):
        with pytest.raises(ValueError, match="expects DIESEL input.*provides FUEL_GAS"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE", "LOWER_HEATING_VALUE": 38}],
                    "UNITS": [
                        {"NAME": "engine", "TYPE": "DIESEL_ENGINE", "INPUT": "fuel", "MODEL": TURBINE},
                    ],
                }
            )

    def test_compatible_chain_accepted(self):
        network = YamlEnergyNetwork.model_validate(
            {
                "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                "UNITS": [
                    {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "MODEL": GENERATOR_SET_MODEL},
                    {"NAME": "motor", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "genset"},
                    {
                        "TYPE": "DRIVE_TRAIN",
                        "INPUT": "motor",
                        "SHAFT": "shaft",
                    },
                ],
            }
        )
        assert len(network.units) == 3


class TestSampledCompressor:
    def test_parses_with_file_and_lookup_variables(self):
        comp = _component_adapter.validate_python(
            {
                "TYPE": "COMPRESSOR_SAMPLED",
                "COMPRESSOR": "C-1",
                "INPUT": "turbine",
                "FILE": "c.csv",
                "RATE": 1000,
            }
        )
        assert isinstance(comp, YamlCompressorSampled)
        assert comp.file == "c.csv"
        assert comp.rate == 1000

    @pytest.mark.parametrize("source_type", ["FUEL_GAS_SOURCE", "ELECTRICAL_SOURCE", "DIESEL_SOURCE"])
    def test_input_must_provide_mechanical_power(self, source_type):
        with pytest.raises(ValueError, match="COMPRESSOR_SAMPLED 'C-1' .* expects MECHANICAL input"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "src", "TYPE": source_type}],
                    "UNITS": [
                        {
                            "TYPE": "COMPRESSOR_SAMPLED",
                            "COMPRESSOR": "C-1",
                            "INPUT": "src",
                            "FILE": "c.csv",
                            "RATE": 1000,
                        }
                    ],
                }
            )

    def test_cannot_be_an_input(self):
        with pytest.raises(ValueError, match="not a known source or provider"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel", "MODEL": TURBINE},
                        {
                            "TYPE": "COMPRESSOR_SAMPLED",
                            "COMPRESSOR": "C-1",
                            "INPUT": "turbine",
                            "FILE": "c.csv",
                            "RATE": 1000,
                        },
                        {"NAME": "load", "TYPE": "MECHANICAL_CONSUMER", "INPUT": "C-1", "LOAD": 5},
                    ],
                }
            )
