import json
from pathlib import Path

import pytest
from ecalc_cli.io.cache import Cache, CacheData
from libecalc.dto.result import EcalcModelResult


@pytest.fixture
def all_energy_usage_models_cache_fixture(request, all_energy_usage_models_dto, tmp_path):
    results_path = (
        Path(request.path).parent.parent
        / "libecalc"
        / "integration"
        / "snapshots"
        / "test_all_energy_usage_models"
        / "test_all_results"
        / "all_energy_usage_models_v3.json"
    )
    with results_path.open() as source:
        cache_data = CacheData(
            results=json.load(source),
            component_dto=all_energy_usage_models_dto.ecalc_model,
        )
        cache = Cache(user_specified_output_path=tmp_path)
        cache.results_path.touch(mode=0o660, exist_ok=True)
        text = cache_data.model_dump_json()
        cache_data.model_dump()
        cache.results_path.write_text(text)
        return cache


class TestLoadResults:
    def test_load_all_energy_usage_models_snapshot(self, all_energy_usage_models_cache_fixture):
        """
        Test created to make sure get_asset_result works as expected
        """
        assert isinstance(all_energy_usage_models_cache_fixture.load_results(), EcalcModelResult)
