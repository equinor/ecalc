import pytest

from libecalc.fixtures import YamlCase


@pytest.fixture(params=["nextgen_yaml", "nextgen_previous_yaml"])
def nextgen_model(request: pytest.FixtureRequest):
    yaml_case: YamlCase = request.getfixturevalue(request.param)
    model = yaml_case.get_yaml_model()
    model.validate_for_run()
    return model


def test_nextgen_example_runs(nextgen_model):
    pipelines, simulations = nextgen_model.get_process_simulations()

    assert len(pipelines) == 4
    assert len(simulations) == 1
    assert len(nextgen_model.get_shafts()) == 4
    assert len(nextgen_model.get_compressors()) == 12
