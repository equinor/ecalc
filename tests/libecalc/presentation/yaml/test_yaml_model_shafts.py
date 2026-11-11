from io import StringIO

import pytest

from libecalc.ecalc_model.process.configuration_handlers import TimeSeriesShaftConfigurationHandler
from libecalc.ecalc_model.process.process_units import TimeSeriesCompressorProcessUnit
from libecalc.energy.models.compressor_shaft_power import compressor_shaft_power
from libecalc.presentation.yaml.domain.energy.compressor import TimeSeriesProcessCompressor
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineCurve, YamlTurbineDefinition
from libecalc.testing.energy_builders import YamlDriveTrainBuilder, YamlEnergyNetworkBuilder
from libecalc.testing.process_builders import (
    YamlDefinitionsBuilder,
    YamlIndividualStreamDistributionBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    compressors_in,
    shaft_for,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder

SHAFT = "Export shaft A"
COMPRESSOR_A = "KA6969 Export compressor A"
COMPRESSOR_B = "KA6970 Export compressor B"


def _asset(mechanical_efficiencies: dict[str, YamlExpressionType]) -> YamlAsset:
    pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("export_pipeline")
        .with_compressor_item(compressor=COMPRESSOR_A)
        .with_compressor_item(compressor=COMPRESSOR_B)
        .validate()
    )
    simulation = (
        YamlProcessSimulationBuilder()
        .with_name("export_simulation")
        .with_pipeline(pipeline)
        .with_stream_distribution(YamlIndividualStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )
    turbine_model = YamlTurbineDefinition(
        lower_heating_value=38, curve=YamlTurbineCurve(load=[10, 20], efficiency=[0.2, 0.3])
    )
    drive_train = YamlDriveTrainBuilder().with_name("export_drive").with_input("export_turbine").with_shaft(SHAFT)
    for compressor, efficiency in mechanical_efficiencies.items():
        drive_train.with_mechanical_efficiency(compressor, efficiency)
    energy_network = (
        YamlEnergyNetworkBuilder()
        .with_test_data()
        .with_gas_turbine(name="export_turbine", input="fuel_gas", model=turbine_model)
        .with_unit(drive_train.validate())
        .validate()
    )
    return (
        YamlAssetBuilder()
        .with_test_data()
        .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        .with_shafts([shaft_for(pipeline, name=SHAFT)])
        .with_compressors(compressors_in(pipeline))
        .with_process_pipelines({pipeline.name: pipeline})
        .with_process_simulations([simulation])
        .with_energy_network(energy_network)
        .validate()
    )


def _model(yaml_model_factory, asset: YamlAsset, variables: dict) -> YamlModel:
    asset_dict = asset.model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)
    asset_dict["VARIABLES"] = variables
    stream = ResourceStream(name="test_model", stream=StringIO(PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)))
    return yaml_model_factory(configuration=stream, resources={})


@pytest.fixture
def model(yaml_model_factory) -> YamlModel:
    return _model(yaml_model_factory, _asset(mechanical_efficiencies={}), variables={})


def test_get_shafts_lists_compressor_ids_without_mapping(model):
    compressor_ids = {compressor.name: compressor.get_id() for compressor in model.get_compressors()}

    [shaft] = model.get_shafts()

    assert shaft.name == SHAFT
    assert shaft.compressor_equipment_ids == (compressor_ids[COMPRESSOR_A], compressor_ids[COMPRESSOR_B])


def test_drive_train_gets_process_compressors_when_energy_is_mapped_first(model):
    _, _, consumers, _ = model.get_energy_network()
    pipelines, _ = model.get_process_simulations()

    drive_train_nodes = [consumer for consumer in consumers if isinstance(consumer, TimeSeriesProcessCompressor)]
    process_compressors = [
        unit for unit in pipelines[0].get_process_units() if isinstance(unit, TimeSeriesCompressorProcessUnit)
    ]
    assert [node.get_name() for node in drive_train_nodes] == [COMPRESSOR_A, COMPRESSOR_B]
    assert [node.process_unit_id for node in drive_train_nodes] == [c.get_id() for c in process_compressors]


def test_compressors_on_one_shaft_share_one_solver_shaft(model):
    _, [simulation] = model.get_process_simulations()
    [problem] = simulation.process_problems
    [shaft] = model.get_shafts()

    [solver_shaft] = [
        handler
        for handler in problem.get_configuration_handlers()
        if isinstance(handler, TimeSeriesShaftConfigurationHandler)
    ]

    assert solver_shaft.get_compressor_ids() == list(shaft.compressor_equipment_ids)


def test_compressor_demands_gas_power_divided_by_its_mechanical_efficiency_in_each_period(yaml_model_factory):
    variables = {"mechanical_efficiency": {"2019-01-01": {"VALUE": 0.95}, "2022-01-01": {"VALUE": 0.90}}}
    asset = _asset(mechanical_efficiencies={COMPRESSOR_A: "$var.mechanical_efficiency"})
    _, _, consumers, periods = _model(yaml_model_factory, asset, variables).get_energy_network()
    gas_power_mw = 10.0

    shaft_power = {
        (node.get_name(), period.start.year): compressor_shaft_power(
            gas_power_mw, node.get_mechanical_efficiency(period)
        ).value
        for node in consumers
        if isinstance(node, TimeSeriesProcessCompressor)
        for period in (periods[0], periods[-1])
    }

    assert shaft_power == {
        (COMPRESSOR_A, 2019): pytest.approx(10.0 / 0.95),
        (COMPRESSOR_A, 2022): pytest.approx(10.0 / 0.90),
        (COMPRESSOR_B, 2019): 10.0,
        (COMPRESSOR_B, 2022): 10.0,
    }
