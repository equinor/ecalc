import pytest

from libecalc.fixtures import YamlCase


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
    assert len(nextgen_model.get_compressors()) == 12
