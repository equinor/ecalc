from collections.abc import Callable
from pathlib import Path

import pytest
from pytestarch import EvaluableArchitecture, get_evaluable_architecture


@pytest.fixture(scope="session")
def root_dir() -> Path:
    root_dir = Path(__file__).parent.parent.parent
    return root_dir / "src" / "libecalc"


@pytest.fixture(scope="session")
def src_dir(root_dir) -> Path:
    return root_dir


@pytest.fixture(scope="session")
def libecalc_architecture(root_dir, src_dir: Path) -> Callable[..., EvaluableArchitecture]:
    def __evaluable_architecture(exclude_external_libraries: bool = True):
        arch = get_evaluable_architecture(
            str(root_dir), str(src_dir), exclude_external_libraries=exclude_external_libraries
        )
        return arch

    return __evaluable_architecture
