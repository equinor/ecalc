from io import StringIO

import pytest

from libecalc.ecalc_model.ecalc_event import EcalcEventService
from libecalc.presentation.yaml.domain.energy.compressor import TimeSeriesProcessCompressor
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineCurve, YamlTurbineDefinition
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.shaft import Shaft
from libecalc.testing.energy_builders import YamlEnergyNetworkBuilder
from libecalc.testing.process_builders import (
    YamlCompressorBuilder,
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


def _asset() -> YamlAsset:
    pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("export_pipeline")
        .with_compressor_item(compressor=COMPRESSOR_A, target=YamlCompressorBuilder().with_test_data().validate())
        .with_compressor_item(compressor=COMPRESSOR_B, target=YamlCompressorBuilder().with_test_data().validate())
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
    energy_network = (
        YamlEnergyNetworkBuilder()
        .with_test_data()
        .with_gas_turbine(name="export_turbine", input="fuel_gas", model=turbine_model)
        .with_drive_train(name="export_drive", input="export_turbine", shaft=SHAFT)
        .validate()
    )
    return (
        YamlAssetBuilder()
        .with_test_data()
        .with_shafts([shaft_for(pipeline, name=SHAFT)])
        .with_compressors(compressors_in(pipeline))
        .with_process_pipelines({pipeline.name: pipeline})
        .with_process_simulations([simulation])
        .with_energy_network(energy_network)
        .validate()
    )


@pytest.fixture
def model(yaml_model_factory) -> YamlModel:
    asset_dict = _asset().model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)
    stream = ResourceStream(name="test_model", stream=StringIO(PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)))
    return yaml_model_factory(configuration=stream, resources={})


def test_get_shafts_lists_compressor_ids_without_mapping(model):
    compressor_ids = {compressor.name: compressor.get_id() for compressor in model.get_compressors()}

    [shaft] = model.get_shafts()

    assert shaft.name == SHAFT
    assert shaft.compressor_ids == (compressor_ids[COMPRESSOR_A], compressor_ids[COMPRESSOR_B])


def test_drive_train_gets_process_compressors_when_energy_is_mapped_first(model):
    _, _, consumers, _ = model.get_energy_network()
    pipelines, _ = model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

    drive_train_nodes = [consumer for consumer in consumers if isinstance(consumer, TimeSeriesProcessCompressor)]
    process_compressors = [unit for unit in pipelines[0].get_process_units() if isinstance(unit, Compressor)]
    assert [node.get_name() for node in drive_train_nodes] == [COMPRESSOR_A, COMPRESSOR_B]
    assert [node.process_unit_id for node in drive_train_nodes] == [c.get_id() for c in process_compressors]


def test_compressors_on_one_shaft_share_one_solver_shaft(model):
    _, [simulation] = model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))
    [problem] = simulation.process_problems
    [shaft] = model.get_shafts()

    [solver_shaft] = [handler for handler in problem.get_configuration_handlers() if isinstance(handler, Shaft)]

    assert solver_shaft.get_compressor_ids() == list(shaft.compressor_ids)
