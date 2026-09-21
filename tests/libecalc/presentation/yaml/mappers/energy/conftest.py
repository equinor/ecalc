import pytest

from libecalc.presentation.yaml.yaml_entities import MemoryResource


@pytest.fixture
def make_resource():
    """Build a MemoryResource from column-name=values kwargs, e.g. make_resource(RATE=rates, FUEL=fuel)."""

    def _make_resource(**columns: list[float]) -> MemoryResource:
        return MemoryResource(headers=list(columns), data=[list(values) for values in columns.values()])

    return _make_resource


# Shared sample table used across both the pure expansion tests and the mapper-level tests:
# a compressor operating at `rate` consumes `fuel` and/or produces `power`, one entry per rate.
@pytest.fixture
def rates() -> list[float]:
    return [1000.0, 2000.0, 3000.0]


@pytest.fixture
def fuel() -> list[float]:
    return [10000.0, 20000.0, 30000.0]


@pytest.fixture
def power() -> list[float]:
    return [5.0, 10.0, 15.0]
