import pytest

from libecalc.domain.resource import Resource
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_units import (
    DieselConsumer,
    DieselSource,
    ElectricalBus,
    ElectricalCable,
    ElectricalConsumer,
    ElectricalMotor,
    ElectricalSource,
    FuelGasConsumer,
    FuelGasManifold,
    FuelGasSource,
    GasTurbine,
    GeneratorSet,
    MechanicalConsumer,
    SampledCompressorElectricalConsumer,
    SampledCompressorFuelGasConsumer,
    SampledCompressorMechanicalConsumer,
)
from libecalc.presentation.yaml.mappers.energy.sampled_compressor_mapper import expand_sampled_compressors
from libecalc.presentation.yaml.mappers.energy_network_mapper import EnergyNetworkMapper
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlEnergyNetwork,
    YamlSampledCompressor,
)


def test_maps_sources_units_connections_and_consumer_expressions(expression_evaluator_factory, period):
    yaml_network = YamlEnergyNetwork.model_validate(
        {
            "SOURCES": [
                {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE", "CAPACITY": 100},
                {"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE", "CAPACITY": 20},
                {"NAME": "diesel", "TYPE": "DIESEL_SOURCE", "CAPACITY": 500},
            ],
            "UNITS": [
                {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "CAPACITY": 10},
                {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel", "CAPACITY": 15},
                {"NAME": "motor", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "genset", "CAPACITY": 5},
                {"NAME": "cable", "TYPE": "ELECTRICAL_CABLE", "INPUT": "grid"},
                {"NAME": "bus", "TYPE": "ELECTRICAL_BUS", "INPUT": ["cable"]},
                {"NAME": "manifold", "TYPE": "FUEL_GAS_MANIFOLD", "INPUT": ["fuel"]},
                {"NAME": "electrical_load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "bus", "LOAD": 5},
                {"NAME": "mechanical_load", "TYPE": "MECHANICAL_CONSUMER", "INPUT": "motor", "LOAD": 2},
                {"NAME": "fuel_load", "TYPE": "FUEL_GAS_CONSUMER", "INPUT": "manifold", "RATE": 10},
                {"NAME": "diesel_load", "TYPE": "DIESEL_CONSUMER", "INPUT": "diesel", "RATE": 20},
            ],
        }
    )

    expression_evaluator = expression_evaluator_factory.from_periods(periods=[period])
    topology, energy_units, consumer_expressions = EnergyNetworkMapper().map_energy_network(
        yaml_network, expression_evaluator
    )

    assert {connection.energy_type for connection in topology.get_connections()} == {
        DieselRate,
        ElectricalPower,
        FuelGasRate,
        MechanicalPower,
    }
    assert len(topology.get_topological_order()) == 13
    assert len(topology.get_connections()) == 10
    assert [type(energy_unit) for energy_unit in energy_units] == [
        FuelGasSource,
        ElectricalSource,
        DieselSource,
        GeneratorSet,
        GasTurbine,
        ElectricalMotor,
        ElectricalCable,
        ElectricalBus,
        FuelGasManifold,
        ElectricalConsumer,
        MechanicalConsumer,
        FuelGasConsumer,
        DieselConsumer,
    ]
    assert [energy_unit.get_name() for energy_unit in energy_units] == [
        "fuel",
        "grid",
        "diesel",
        "genset",
        "turbine",
        "motor",
        "cable",
        "bus",
        "manifold",
        "electrical_load",
        "mechanical_load",
        "fuel_load",
        "diesel_load",
    ]
    assert {energy_unit.get_id() for energy_unit in energy_units} == set(topology.get_nodes())
    consumer_ids_by_name = {energy_unit.get_name(): energy_unit.get_id() for energy_unit in energy_units}
    assert {
        consumer_ids_by_name["electrical_load"]: 5,
        consumer_ids_by_name["mechanical_load"]: 2,
        consumer_ids_by_name["fuel_load"]: 10,
        consumer_ids_by_name["diesel_load"]: 20,
    } == {
        energy_unit_id: expression.get_original_expression()
        for energy_unit_id, expression in consumer_expressions.items()
    }


def _sampled_compressor_network(
    headers: list[str], rows: list[list[float]], input_name: str, source: dict
) -> tuple[YamlEnergyNetwork, dict[str, Resource]]:
    yaml_network = YamlEnergyNetwork.model_validate(
        {
            "SOURCES": [source],
            "UNITS": [
                {
                    "NAME": "compressor",
                    "TYPE": "SAMPLED_COMPRESSOR",
                    "INPUT": input_name,
                    "FILE": "compressor.csv",
                    "RATE": 50000,
                },
            ],
        }
    )
    facility_resources: dict[str, Resource] = {
        "compressor.csv": MemoryResource(headers=headers, data=[list(column) for column in zip(*rows)])
    }
    return expand_sampled_compressors(yaml_network, facility_resources), facility_resources


@pytest.mark.parametrize(
    ("headers", "rows", "input_name", "source", "expected_types", "expected_energy_types"),
    [
        (
            ["RATE", "FUEL"],
            [[1000, 100], [2000, 150]],
            "fuel",
            {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"},
            [FuelGasSource, SampledCompressorFuelGasConsumer],
            {FuelGasRate},
        ),
        (
            ["RATE", "POWER"],
            [[1000, 1.0], [2000, 1.5]],
            "grid",
            {"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE"},
            [ElectricalSource, SampledCompressorElectricalConsumer],
            {ElectricalPower},
        ),
        (
            ["RATE", "FUEL", "POWER"],
            [[1000, 100, 1.0], [2000, 150, 1.5]],
            "fuel",
            {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"},
            [FuelGasSource, GasTurbine, SampledCompressorMechanicalConsumer],
            {FuelGasRate, MechanicalPower},
        ),
    ],
)
def test_maps_expanded_sampled_compressor_units(
    headers,
    rows,
    input_name,
    source,
    expected_types,
    expected_energy_types,
    expression_evaluator_factory,
    period,
):
    """Each _Sampled* subclass must map to its own energy unit type, wired against the
    real SampledCompressor curve built from FILE - not a curve-less generic consumer.
    All four subclasses share YamlSampledCompressor as their base, so _map_unit's match
    arms only resolve correctly while the YamlSampledCompressor arm stays last."""
    expanded, facility_resources = _sampled_compressor_network(headers, rows, input_name, source)
    expression_evaluator = expression_evaluator_factory.from_periods(periods=[period])

    network, energy_units, consumer_expressions = EnergyNetworkMapper().map_energy_network(
        expanded, expression_evaluator, facility_resources
    )

    assert [type(energy_unit) for energy_unit in energy_units] == expected_types
    assert {connection.energy_type for connection in network.get_connections()} == expected_energy_types
    assert energy_units[0].get_name() == source["NAME"]
    assert energy_units[-1].get_name() == "compressor"
    # A sampled unit's RATE is a query against FILE's curve, not an energy usage value,
    # so it must not be turned into a consumer expression (deriving energy usage from
    # FILE is not yet implemented).
    assert consumer_expressions == {}


def test_turbine_and_compressor_split_shares_the_same_curve_and_derives_fuel_from_power(
    expression_evaluator_factory, period
):
    """The turbine's fuel draw must come from backward energy propagation against its
    own real power_to_fuel curve (built from the same FILE as the compressor), not a
    curve-less identity function - this is the crux of the turbine+compressor split."""
    expanded, facility_resources = _sampled_compressor_network(
        ["RATE", "FUEL", "POWER"],
        [[1000, 100, 1.0], [2000, 150, 1.5], [3000, 200, 2.0]],
        "fuel",
        {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"},
    )
    turbine, compressor = expanded.units
    assert turbine.name != compressor.name
    assert compressor.input == turbine.name

    expression_evaluator = expression_evaluator_factory.from_periods(periods=[period])
    _, energy_units, _ = EnergyNetworkMapper().map_energy_network(expanded, expression_evaluator, facility_resources)
    _, turbine_unit, compressor_unit = energy_units

    assert isinstance(turbine_unit, GasTurbine)
    assert isinstance(compressor_unit, SampledCompressorMechanicalConsumer)

    # The compressor demands 1.25 MW mechanical power at rate=1500 (interpolated
    # between the 1.0 and 1.5 samples); the turbine must convert that into the
    # matching interpolated fuel value (125.0), using its own real curve.
    demand = compressor_unit.get_energy(rate=1500)
    assert demand == pytest.approx(1.25)
    assert turbine_unit.get_input_energy(MechanicalPower(demand)).value == pytest.approx(125.0)


def test_turbine_and_compressor_split_reports_zero_fuel_when_switched_off(expression_evaluator_factory, period):
    """A rate<=0 demand means the compressor is switched off - the turbine must report
    zero fuel for the resulting zero power demand, not the minimum sampled power's fuel
    value (which the below-minimum clamp uses for 0 < power < minimum sampled power)."""
    expanded, facility_resources = _sampled_compressor_network(
        ["RATE", "FUEL", "POWER"],
        [[1000, 100, 1.0], [2000, 150, 1.5], [3000, 200, 2.0]],
        "fuel",
        {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"},
    )
    expression_evaluator = expression_evaluator_factory.from_periods(periods=[period])
    _, energy_units, _ = EnergyNetworkMapper().map_energy_network(expanded, expression_evaluator, facility_resources)
    _, turbine_unit, compressor_unit = energy_units

    demand = compressor_unit.get_energy(rate=0)
    assert demand == pytest.approx(0.0)
    assert turbine_unit.get_input_energy(MechanicalPower(demand)).value == pytest.approx(0.0)


def test_power_only_mechanical_consumer_reads_energy_usage_not_power(expression_evaluator_factory, period):
    """A SAMPLED_COMPRESSOR downstream of an explicitly modelled GAS_TURBINE (FILE has
    only POWER, no FUEL) must not be split - it maps to a single
    SampledCompressorMechanicalConsumer, reading energy_usage (=POWER's own values)
    directly, since no power_interpolation_values are present to resolve a separate
    power value from."""
    yaml_network = YamlEnergyNetwork.model_validate(
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
    facility_resources: dict[str, Resource] = {
        "compressor.csv": MemoryResource(
            headers=["RATE", "POWER"], data=[list(column) for column in zip(*[[1000, 1.0], [2000, 1.5]])]
        )
    }
    expanded = expand_sampled_compressors(yaml_network, facility_resources)

    expression_evaluator = expression_evaluator_factory.from_periods(periods=[period])
    _, energy_units, _ = EnergyNetworkMapper().map_energy_network(expanded, expression_evaluator, facility_resources)
    _, turbine_unit, compressor_unit = energy_units

    assert isinstance(turbine_unit, GasTurbine)
    assert isinstance(compressor_unit, SampledCompressorMechanicalConsumer)
    # If this had incorrectly resolved to reading a resolved power value instead of
    # energy_usage, this would raise instead of returning energy_usage's interpolated
    # 1.25 (FILE has no FUEL column, so SampledCompressor never populates power here).
    assert compressor_unit.get_energy(rate=1500) == pytest.approx(1.25)


def test_mapping_an_unexpanded_sampled_compressor_raises():
    """EnergyNetworkMapper never reads FILE itself for an unresolved unit, so it cannot
    resolve a plain YamlSampledCompressor into a unit - expand_sampled_compressors must
    have run first."""
    unit = YamlSampledCompressor.model_validate(
        {
            "NAME": "compressor",
            "TYPE": "SAMPLED_COMPRESSOR",
            "INPUT": "fuel",
            "FILE": "compressor.csv",
            "RATE": 50000,
        }
    )
    with pytest.raises(AssertionError, match="unresolved SAMPLED_COMPRESSOR reached _map_unit"):
        EnergyNetworkMapper()._map_unit(unit, {})
