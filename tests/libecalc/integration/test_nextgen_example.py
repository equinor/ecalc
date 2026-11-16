from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader
from libecalc.fixtures.cases.nextgen.reference_model import MODEL_FILE_NAME, export_reference_model


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
    model = nextgen_yaml.get_yaml_model()
    model.validate_for_run()
    return model


def test_nextgen_example_runs(nextgen_model):
    pipelines, simulations = nextgen_model.get_process_simulations()

    assert len(pipelines) == 4
    assert len(simulations) == 1
    assert len(nextgen_model.get_shafts()) == 4
    assert len(nextgen_model.get_compressors()) == 12
