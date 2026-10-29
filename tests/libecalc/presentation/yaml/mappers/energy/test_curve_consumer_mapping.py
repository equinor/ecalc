import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergyNetwork

GENERATOR = {"CURVE": {"POWER": [5, 10], "FUEL": [20000, 35000]}}


def _network(consumer_type: str, consumer_input: str, curve: dict) -> YamlEnergyNetwork:
    return YamlEnergyNetwork.model_validate(
        {
            "SOURCES": [
                {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"},
            ],
            "UNITS": [
                {"NAME": "genset", "TYPE": "GENERATOR", "INPUT": "fuel", "MODEL": GENERATOR},
                {
                    "NAME": "pump",
                    "TYPE": consumer_type,
                    "INPUT": consumer_input,
                    "LOAD": {"CURVE": curve, "VARIABLE": 2500},
                },
            ],
        }
    )


def _rate_network(consumer_type: str, source_type: str, curve: dict) -> YamlEnergyNetwork:
    return YamlEnergyNetwork.model_validate(
        {
            "SOURCES": [{"NAME": "source", "TYPE": source_type}],
            "UNITS": [
                {
                    "NAME": "flare",
                    "TYPE": consumer_type,
                    "INPUT": "source",
                    "RATE": {"CURVE": curve, "VARIABLE": 2500},
                },
            ],
        }
    )


class TestRateCurve:
    def test_fuel_gas_consumer_rate_curve_maps_to_fuel_gas_rate(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, rates, fuel
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            _rate_network("FUEL_GAS_CONSUMER", "FUEL_GAS_SOURCE", {"VARIABLE": rates, "FUEL": fuel}),
            evaluator,
            resources={},
        )

        (flare,) = consumers
        assert flare.get_name() == "flare"
        assert flare.get_demand(period) == FuelGasRate(25000.0)

    def test_diesel_consumer_rate_curve_maps_to_diesel_rate(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, rates, fuel
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            _rate_network("DIESEL_CONSUMER", "DIESEL_SOURCE", {"VARIABLE": rates, "FUEL": fuel}),
            evaluator,
            resources={},
        )

        (engine,) = consumers
        assert engine.get_demand(period) == DieselRate(25000.0)

    def test_fuel_gas_consumer_file_curve(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource, rates, fuel
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            _rate_network("FUEL_GAS_CONSUMER", "FUEL_GAS_SOURCE", {"FILE": "flare.csv"}),
            evaluator,
            resources={"flare.csv": make_resource(VARIABLE=rates, FUEL=fuel)},
        )

        (flare,) = consumers
        assert flare.get_demand(period) == FuelGasRate(25000.0)

    def test_legacy_tabulated_file_is_reusable_unmodified(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource
    ):
        """Same data as the legacy TABULAR/TABULATED fixture `einput/tabular.csv` (VARIABLE1,FUEL header,
        case-insensitive match on FUEL), proving it can be reused unmodified as a RATE curve FILE."""
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "source", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {
                            "NAME": "tabulated",
                            "TYPE": "FUEL_GAS_CONSUMER",
                            "INPUT": "source",
                            "RATE": {"CURVE": {"FILE": "tabular.csv"}, "VARIABLE": 30000},
                        },
                    ],
                }
            ),
            evaluator,
            resources={
                "tabular.csv": make_resource(
                    VARIABLE1=[0, 20000, 40000, 60000, 80000],
                    FUEL=[0, 1000, 2000, 3000, 4000],
                )
            },
        )

        (tabulated,) = consumers
        assert tabulated.get_demand(period) == FuelGasRate(1500.0)


class TestMapperInline:
    def test_electrical_consumer_load_curve_maps_to_electrical_power(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, rates, power
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            _network("ELECTRICAL_CONSUMER", "genset", {"VARIABLE": rates, "POWER": power}), evaluator, resources={}
        )

        (pump,) = consumers
        assert pump.get_name() == "pump"
        assert pump.get_input_energy_type() is ElectricalPower
        assert pump.get_demand(period) == ElectricalPower(12.5)

    def test_mechanical_consumer_load_curve_maps_to_mechanical_power(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, rates, power
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR", "INPUT": "fuel", "MODEL": GENERATOR},
                        {
                            "NAME": "motor",
                            "TYPE": "ELECTRICAL_MOTOR",
                            "INPUT": "genset",
                            "CAPACITY": 100,
                            "EFFICIENCY": 1.0,
                        },
                        {
                            "NAME": "pump",
                            "TYPE": "MECHANICAL_CONSUMER",
                            "INPUT": "motor",
                            "LOAD": {"CURVE": {"VARIABLE": rates, "POWER": power}, "VARIABLE": 2500},
                        },
                    ],
                }
            ),
            evaluator,
            resources={},
        )

        (pump,) = consumers
        assert pump.get_input_energy_type() is MechanicalPower
        assert pump.get_demand(period) == MechanicalPower(12.5)


class TestMapperFile:
    def test_file_curve_resolves_energy_from_fixed_header(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource, rates, power
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            _network("ELECTRICAL_CONSUMER", "genset", {"FILE": "pump.csv"}),
            evaluator,
            resources={"pump.csv": make_resource(RATE=rates, POWER=power)},
        )

        (pump,) = consumers
        assert pump.get_demand(period) == ElectricalPower(12.5)

    def test_file_variable_column_can_have_any_name(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource, rates, power
    ):
        """The variable column isn't locked to a fixed name like RATE - whichever column isn't the
        energy column is the variable, whatever it's called (e.g. DRILLPRED)."""
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            _network("ELECTRICAL_CONSUMER", "genset", {"FILE": "pump.csv"}),
            evaluator,
            resources={"pump.csv": make_resource(DRILLPRED=rates, POWER=power)},
        )

        (pump,) = consumers
        assert pump.get_demand(period) == ElectricalPower(12.5)

    def test_file_with_extra_column_rejected(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource, rates, power
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        with pytest.raises(EcalcValidationException, match="must have exactly two columns"):
            energy_network_mapper_factory().map_energy_network(
                _network("ELECTRICAL_CONSUMER", "genset", {"FILE": "pump.csv"}),
                evaluator,
                resources={"pump.csv": make_resource(RATE=rates, POWER=power, SUCTION_PRESSURE=[1.0] * len(rates))},
            )

    def test_file_missing_energy_column_rejected(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource, rates, fuel
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        with pytest.raises(EcalcValidationException, match="must have exactly two columns"):
            energy_network_mapper_factory().map_energy_network(
                _network("ELECTRICAL_CONSUMER", "genset", {"FILE": "pump.csv"}),
                evaluator,
                resources={"pump.csv": make_resource(RATE=rates, FUEL=fuel)},
            )

    def test_file_headers_are_case_insensitive(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource, rates, power
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            _network("ELECTRICAL_CONSUMER", "genset", {"FILE": "pump.csv"}),
            evaluator,
            resources={"pump.csv": make_resource(rate=rates, power=power)},
        )

        (pump,) = consumers
        assert pump.get_demand(period) == ElectricalPower(12.5)

    def test_missing_resource_rejected(self, energy_network_mapper_factory, expression_evaluator_factory, period):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        with pytest.raises(EcalcValidationException, match="FILE 'pump.csv' not found"):
            energy_network_mapper_factory().map_energy_network(
                _network("ELECTRICAL_CONSUMER", "genset", {"FILE": "pump.csv"}), evaluator, resources={}
            )


class TestOutsideRange:
    def test_variable_outside_sampled_range_raises_on_demand(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, power
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR", "INPUT": "fuel", "MODEL": GENERATOR},
                        {
                            "NAME": "pump",
                            "TYPE": "ELECTRICAL_CONSUMER",
                            "INPUT": "genset",
                            "LOAD": {
                                "CURVE": {"VARIABLE": [1000.0, 2000.0, 3000.0], "POWER": power},
                                "VARIABLE": 999_999,
                            },
                        },
                    ],
                }
            ),
            evaluator,
            resources={},
        )

        (pump,) = consumers
        with pytest.raises(InvalidEnergyNetworkInputError, match="outside the model's sampled range"):
            pump.get_demand(period)

    def test_variable_below_range_raises_on_demand(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, power
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _topology, _factories, consumers = energy_network_mapper_factory().map_energy_network(
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR", "INPUT": "fuel", "MODEL": GENERATOR},
                        {
                            "NAME": "pump",
                            "TYPE": "ELECTRICAL_CONSUMER",
                            "INPUT": "genset",
                            "LOAD": {
                                "CURVE": {"VARIABLE": [1000.0, 2000.0, 3000.0], "POWER": power},
                                "VARIABLE": 0,
                            },
                        },
                    ],
                }
            ),
            evaluator,
            resources={},
        )

        (pump,) = consumers
        with pytest.raises(InvalidEnergyNetworkInputError, match="outside the model's sampled range"):
            pump.get_demand(period)


class TestYamlValidation:
    def test_invalid_inline_curve_rejected(self):
        with pytest.raises(Exception, match="strictly"):
            YamlEnergyNetwork.model_validate(
                {
                    "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
                    "UNITS": [
                        {"NAME": "genset", "TYPE": "GENERATOR", "INPUT": "fuel", "MODEL": GENERATOR},
                        {
                            "NAME": "pump",
                            "TYPE": "ELECTRICAL_CONSUMER",
                            "INPUT": "genset",
                            "LOAD": {
                                "CURVE": {"VARIABLE": [1000.0, 1000.0], "POWER": [1.0, 2.0]},
                                "VARIABLE": 0,
                            },
                        },
                    ],
                }
            )
