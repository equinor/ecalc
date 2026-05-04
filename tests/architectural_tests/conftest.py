from pathlib import Path

import pytest
from pytestarch import EvaluableArchitecture, get_evaluable_architecture


@pytest.fixture(scope="function")
def root_dir() -> Path:
    root_dir = Path(__file__).parent.parent.parent.parent / "libecalc" / "src" / "libecalc"
    return root_dir


@pytest.fixture(scope="function")
def src_dir(root_dir) -> Path:
    return root_dir.parent / "libecalc"


@pytest.fixture(scope="function")
def libecalc_architecture(root_dir, src_dir: Path) -> EvaluableArchitecture:
    return get_evaluable_architecture(str(root_dir), str(src_dir))
