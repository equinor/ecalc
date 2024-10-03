from datetime import datetime

import pytest
from inline_snapshot import snapshot

import libecalc.dto.fuel_type
from libecalc.common.time_utils import Period
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException
from libecalc.presentation.yaml.mappers.component_mapper import _resolve_fuel
from libecalc.presentation.yaml.yaml_entities import References


@pytest.fixture
def references():
    return References(
        fuel_types={
            "fuel_gas": libecalc.dto.fuel_type.FuelType(
                name="fuel_gas",
                emissions=[],
            ),
            "diesel": libecalc.dto.fuel_type.FuelType(
                name="diesel",
                emissions=[],
            ),
        }
    )


@pytest.fixture
def all_the_time():
    return Period()


class TestResolveFuel:
    def test_none(self, references, all_the_time):
        assert _resolve_fuel(None, None, references, target_period=all_the_time) is None

    def test_parent_fuel(self, references, all_the_time):
        assert _resolve_fuel(None, "diesel", references, target_period=all_the_time).popitem()[1].name == "diesel"

    def test_consumer_fuel(self, references, all_the_time):
        assert _resolve_fuel("diesel", None, references, target_period=all_the_time).popitem()[1].name == "diesel"

    def test_both(self, references, all_the_time):
        assert _resolve_fuel("diesel", "fuel_gas", references, target_period=all_the_time).popitem()[1].name == "diesel"

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_invalid(self, references, all_the_time):
        with pytest.raises(InvalidReferenceException) as exc_info:
            assert (
                _resolve_fuel("diessel", "fuel_gass", references, target_period=all_the_time).popitem()[1] == "diessel"
            )
        assert str(exc_info.value) == snapshot(
            "Invalid fuel reference 'diessel'. Available references: fuel_gas, diesel"
        )

    def test_resolve_multiple_fuels(self, references, all_the_time):
        _resolve_fuel(
            {datetime(1900, 1, 1): "diesel", datetime(2020, 1, 1): "fuel_gas"},
            "fuel_gas",
            references,
            target_period=all_the_time,
        )
