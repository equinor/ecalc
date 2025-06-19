from datetime import datetime

import pytest

from libecalc.application.graph_result import GraphResult
from libecalc.domain.process.process_change_event import ProcessChangedEvent
from libecalc.fixtures import YamlCase
from libecalc.presentation.json_result.mapper import get_asset_result


@pytest.fixture
def graph_result(all_energy_usage_models_yaml: YamlCase) -> GraphResult:
    model = all_energy_usage_models_yaml.get_yaml_model()
    model.validate_for_run()
    model.evaluate_energy_usage()
    model.evaluate_emissions()
    model.evaluate_process_results()
    event = ProcessChangedEvent(start=datetime(2018, 1, 1), name=str(datetime(2018, 1, 1)))
    process_system = model._graph.get_node("late_start_consumer").get_process_system(event)
    return model.get_graph_result()


@pytest.mark.snapshot
def test_all_results(graph_result, rounded_snapshot):
    snapshot_name = "all_energy_usage_models_v3.json"

    asset_result = get_asset_result(graph_result).model_dump()
    rounded_snapshot(data=asset_result, snapshot_name=snapshot_name)
