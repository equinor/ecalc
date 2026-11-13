import pytest

from libecalc.fixtures import YamlCase
from libecalc.presentation.yaml.domain.energy import TimeSeriesCompressorSampled


@pytest.fixture
def nextgen_model(nextgen_yaml: YamlCase):
    model = nextgen_yaml.get_yaml_model()
    model.validate_for_run()
    return model


def test_nextgen_example_runs(nextgen_model):
    pipelines, simulations = nextgen_model.get_process_simulations()

    assert len(pipelines) == 4
    assert len(simulations) == 1
    assert len(nextgen_model.get_shafts()) == 4
    assert len(nextgen_model.get_compressors()) == 10


def test_nextgen_example_sampled_compressors_give_shaft_power(nextgen_model):
    _, _, consumers, periods = nextgen_model.get_energy_network()

    sampled_compressors = [consumer for consumer in consumers if isinstance(consumer, TimeSeriesCompressorSampled)]

    assert sorted(compressor.get_name() for compressor in sampled_compressors) == [
        "sampled_el_compressor",
        "sampled_mech_compressor",
    ]
    for compressor in sampled_compressors:
        assert all(compressor.get_shaft_power(period).value > 0 for period in periods)
