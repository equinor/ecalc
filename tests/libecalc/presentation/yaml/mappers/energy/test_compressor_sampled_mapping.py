from io import StringIO

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.ecalc_model.equipment.compressor_equipment import CompressorEquipment
from libecalc.energy.energy_types import MechanicalPower
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.presentation.yaml.domain.energy import TimeSeriesCompressorSampled
from libecalc.presentation.yaml.mappers.model import ResourceValidationException
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlCompressorSampled,
    YamlEnergyNetwork,
    YamlEnergySourceType,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineCurve, YamlTurbineDefinition
from libecalc.presentation.yaml.yaml_types.yaml_compressor import YamlCompressor
from libecalc.testing.energy_builders import (
    YamlCompressorSampledBuilder,
    YamlElectricalMotorBuilder,
    YamlEnergyNetworkBuilder,
    YamlEnergySourceBuilder,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder

COMPRESSOR_NAME = "23KA001 Gas Compressor"
COMPRESSOR_EQUIPMENT_ID = CompressorEquipment(name=COMPRESSOR_NAME).get_id()
COMPRESSOR_EQUIPMENT_IDS = {COMPRESSOR_NAME: COMPRESSOR_EQUIPMENT_ID}
TURBINE_MODEL = YamlTurbineDefinition(
    lower_heating_value=38, curve=YamlTurbineCurve(load=[5, 10, 20], efficiency=[0.2, 0.3, 0.35])
)


def _unit_builder(
    compressor: str = COMPRESSOR_NAME,
    input: str = "turbine",
    file: str = "compressor.csv",
    rate: YamlExpressionType = 2500,
) -> YamlCompressorSampledBuilder:
    return YamlCompressorSampledBuilder().with_compressor(compressor).with_input(input).with_file(file).with_rate(rate)


def _unit(**kwargs) -> YamlCompressorSampled:
    return _unit_builder(**kwargs).validate()


def _source(name: str, source_type: YamlEnergySourceType):
    return YamlEnergySourceBuilder().with_name(name).with_type(source_type).validate()


def _network(compressor_input: str = "turbine", **unit_kwargs) -> YamlEnergyNetwork:
    return (
        YamlEnergyNetworkBuilder()
        .with_sources(
            [
                _source("fuel", YamlEnergySourceType.FUEL_GAS_SOURCE),
                _source("el", YamlEnergySourceType.ELECTRICAL_SOURCE),
            ]
        )
        .with_gas_turbine("turbine", "fuel", TURBINE_MODEL)
        .with_unit(YamlElectricalMotorBuilder().with_name("motor").with_input("el").validate())
        .with_unit(_unit(input=compressor_input, **unit_kwargs))
        .validate()
    )


def _connections_by_name(topology, nodes) -> set[tuple[str, str]]:
    names = {node.get_id(): node.get_name() for node in nodes}
    return {(names[c.source_id], names[c.target_id]) for c in topology.get_connections()}


def _map(energy_network_mapper_factory, expression_evaluator_factory, period, network, resources):
    evaluator = expression_evaluator_factory.from_periods(periods=[period])
    return energy_network_mapper_factory(compressor_equipment_ids=COMPRESSOR_EQUIPMENT_IDS).map_energy_network(
        network, evaluator, resources=resources
    )


class TestMapperErrors:
    def test_missing_resource_rejected(self, energy_network_mapper_factory, expression_evaluator_factory, period):
        with pytest.raises(EcalcValidationException, match="FILE 'compressor.csv' not found"):
            _map(energy_network_mapper_factory, expression_evaluator_factory, period, _network(), resources={})

    def test_invalid_column_points_to_the_file_and_column(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource, rates, fuel
    ):
        with pytest.raises(ResourceValidationException, match=f"'{COMPRESSOR_NAME}': Column 'FUEL'") as error:
            _map(
                energy_network_mapper_factory,
                expression_evaluator_factory,
                period,
                _network(),
                {"compressor.csv": make_resource(RATE=rates, FUEL=fuel)},
            )
        assert error.value.file_context.name == "compressor.csv"
        assert error.value.file_context.start.column == "FUEL"

    def test_column_without_given_variable_points_to_the_file_and_column(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource
    ):
        resource = make_resource(
            RATE=[1000.0, 2000.0, 1000.0, 2000.0],
            SUCTION_PRESSURE=[10.0, 10.0, 20.0, 20.0],
            SHAFT_POWER=[1.0, 2.0, 1.5, 3.0],
        )
        with pytest.raises(ResourceValidationException, match="column for SUCTION_PRESSURE") as error:
            _map(
                energy_network_mapper_factory,
                expression_evaluator_factory,
                period,
                _network(),
                {"compressor.csv": resource},
            )
        assert error.value.file_context.name == "compressor.csv"
        assert error.value.file_context.start.column == "SUCTION_PRESSURE"

    def test_unequal_column_lengths_point_to_the_file(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource
    ):
        resource = make_resource(RATE=[1000.0, 2000.0, 3000.0], SHAFT_POWER=[1.0, 2.0])
        with pytest.raises(ResourceValidationException) as error:
            _map(
                energy_network_mapper_factory,
                expression_evaluator_factory,
                period,
                _network(),
                {"compressor.csv": resource},
            )
        assert error.value.file_context.name == "compressor.csv"


class TestMapper:
    @pytest.mark.parametrize("compressor_input", ["turbine", "motor"])
    def test_maps_to_compressor_sampled_fed_mechanical_power(
        self,
        compressor_input,
        energy_network_mapper_factory,
        expression_evaluator_factory,
        period,
        make_resource,
        rates,
        shaft_power,
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        topology, factories, consumers = energy_network_mapper_factory(
            compressor_equipment_ids=COMPRESSOR_EQUIPMENT_IDS
        ).map_energy_network(
            _network(compressor_input),
            evaluator,
            resources={"compressor.csv": make_resource(RATE=rates, SHAFT_POWER=shaft_power)},
        )

        (compressor,) = consumers
        assert isinstance(compressor, TimeSeriesCompressorSampled)
        assert compressor.get_name() == COMPRESSOR_NAME
        assert compressor.compressor_equipment_id == COMPRESSOR_EQUIPMENT_ID
        assert compressor.file == "compressor.csv"
        assert compressor.get_input_energy_type() is MechanicalPower
        assert compressor.get_shaft_power(period) == MechanicalPower(12.5)
        assert (compressor_input, COMPRESSOR_NAME) in _connections_by_name(topology, [*factories, *consumers])
        (incoming,) = topology.get_incoming_connections(compressor.get_id())
        assert incoming.energy_type is MechanicalPower

    @pytest.mark.parametrize("compressor_input", ["fuel", "el"])
    def test_non_mechanical_input_rejected(self, compressor_input):
        with pytest.raises(ValueError, match=f"expects MECHANICAL input, but '{compressor_input}' provides"):
            _network(compressor_input)

    def test_rate_outside_sampled_range_rejected(
        self, energy_network_mapper_factory, expression_evaluator_factory, period, make_resource, shaft_power
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        _, _, consumers = energy_network_mapper_factory(
            compressor_equipment_ids=COMPRESSOR_EQUIPMENT_IDS
        ).map_energy_network(
            _network(rate=999_999),
            evaluator,
            resources={"compressor.csv": make_resource(RATE=[1000.0, 2000.0, 3000.0], SHAFT_POWER=shaft_power)},
        )

        (compressor,) = consumers
        with pytest.raises(InvalidEnergyNetworkInputError, match="outside the model's sampled range"):
            compressor.get_shaft_power(period)


class TestYamlCompressorSampled:
    def test_requires_a_lookup_variable(self):
        with pytest.raises(ValueError, match="at least one of RATE, SUCTION_PRESSURE or DISCHARGE_PRESSURE"):
            YamlCompressorSampledBuilder().with_compressor("C-1").with_input("turbine").with_file("comp.csv").validate()

    def test_negative_rate_rejected(self):
        with pytest.raises(ValueError, match="RATE must be non-negative"):
            _unit(rate=-1)

    def test_compressor_name_colliding_with_a_unit_name_rejected(self):
        DUPLICATE_COMPRESSOR_NAME = "shared name"
        network = (
            YamlEnergyNetworkBuilder()
            .with_sources([_source("fuel", YamlEnergySourceType.FUEL_GAS_SOURCE)])
            .with_gas_turbine(DUPLICATE_COMPRESSOR_NAME, "fuel", TURBINE_MODEL)
            .with_unit(_unit(compressor=DUPLICATE_COMPRESSOR_NAME, input=DUPLICATE_COMPRESSOR_NAME))
        )
        with pytest.raises(ValueError, match=f"Duplicate names.*{DUPLICATE_COMPRESSOR_NAME}"):
            network.validate()


def _asset(file: str) -> YamlAsset:
    energy_network = (
        YamlEnergyNetworkBuilder()
        .with_sources([_source("fuel", YamlEnergySourceType.FUEL_GAS_SOURCE)])
        .with_gas_turbine("turbine", "fuel", TURBINE_MODEL)
        .with_unit(_unit(file=file, rate=1500))
        .validate()
    )
    return (
        YamlAssetBuilder()
        .with_test_data()
        .with_start("2020-01-01")
        .with_end("2021-01-01")
        .with_compressors([YamlCompressor(name=COMPRESSOR_NAME)])
        .with_energy_network(energy_network)
        .validate()
    )


def _yaml_model(yaml_model_factory, resources: dict[str, MemoryResource], file: str = "compressor.csv"):
    asset_dict = _asset(file).model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)
    stream = ResourceStream(name="model.yaml", stream=StringIO(PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)))
    return yaml_model_factory(configuration=stream, resources=resources)


class TestEndToEnd:
    def test_shaft_power(self, yaml_model_factory, make_resource, rates, shaft_power):
        model = _yaml_model(yaml_model_factory, {"compressor.csv": make_resource(RATE=rates, SHAFT_POWER=shaft_power)})
        topology, factories, consumers, _periods = model.get_energy_network()

        assert topology is not None
        assert len(topology.get_nodes()) == 3
        assert len(topology.get_connections()) == 2
        assert [f.get_name() for f in factories] == ["fuel", "turbine"]
        (compressor,) = consumers
        assert isinstance(compressor, TimeSeriesCompressorSampled)
        assert compressor.get_shaft_power(model.get_periods()[0]) == MechanicalPower(7.5)

    def test_unknown_file_reported_at_validation(self, yaml_model_factory):
        model = _yaml_model(yaml_model_factory, {}, file="missing.csv")
        with pytest.raises(ModelValidationException, match="resource not found, got 'missing.csv'"):
            model.validate_for_run()

    def test_invalid_file_reported_in_the_file(self, yaml_model_factory, make_resource, rates, fuel):
        model = _yaml_model(yaml_model_factory, {"compressor.csv": make_resource(RATE=rates, FUEL=fuel)})
        with pytest.raises(ModelValidationException, match="Column 'FUEL' is not supported") as error:
            model.get_energy_network()
        (validation_error,) = error.value.errors()
        assert validation_error.file_context.name == "compressor.csv"
        assert validation_error.file_context.start.column == "FUEL"
