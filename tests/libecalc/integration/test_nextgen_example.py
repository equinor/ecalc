from pathlib import Path

import pytest

from libecalc.ecalc_model.process.pump.pump_simulation_evaluation import evaluate_pump_simulation
from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader
from libecalc.fixtures.cases.nextgen.reference_model import MODEL_FILE_NAME, export_reference_model
from libecalc.presentation.yaml.domain.energy import TimeSeriesCompressorSampled


@pytest.fixture
def nextgen_yaml(tmp_path: Path) -> YamlCase:
    exported = export_reference_model(tmp_path)
    return YamlCaseLoader.load(
        case_path=tmp_path,
        main_file=MODEL_FILE_NAME,
        resource_names=[path.name for path in exported if path.name != MODEL_FILE_NAME],
    )


@pytest.fixture
def nextgen_model(nextgen_yaml: YamlCase):
    model = nextgen_yaml.get_yaml_model(nextgen=True)
    model.validate_for_run()
    return model


def test_nextgen_example_is_valid(nextgen_yaml: YamlCase):
    model = nextgen_yaml.get_yaml_model(nextgen=True)

    assert model.validate_nextgen() is model


def test_nextgen_example_runs(nextgen_model):
    pipelines, simulations = nextgen_model.get_process_simulations()

    assert len(pipelines) == 4
    assert len(simulations) == 1
    assert len(nextgen_model.get_shafts()) == 4
    assert len(nextgen_model.get_compressors()) == 10


def test_nextgen_example_pumps_are_valid_in_every_period(nextgen_model):
    pump_pipelines, [pump_simulation] = nextgen_model.get_pump_simulations()

    result = evaluate_pump_simulation(pump_simulation, pump_pipelines)

    assert all(period_result.is_valid for period_result in result.period_results)
    # Both pumps run until 2028. From then one pump takes the rate, which is below the chart's maximum rate of
    # 980 m3/h.
    assert [period_result.selected_setting_index for period_result in result.period_results] == [1] * 8 + [0] * 14


def test_nextgen_example_sampled_compressors_give_mechanical_power(nextgen_model):
    _, _, consumers, periods = nextgen_model.get_energy_network()

    sampled_compressors = [consumer for consumer in consumers if isinstance(consumer, TimeSeriesCompressorSampled)]

    assert sorted(compressor.get_name() for compressor in sampled_compressors) == [
        "sampled_el_compressor",
        "sampled_mech_compressor",
    ]
    for compressor in sampled_compressors:
        assert all(compressor.get_mechanical_power(period).value > 0 for period in periods)
