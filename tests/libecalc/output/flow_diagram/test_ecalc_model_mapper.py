import json
from datetime import datetime
from unittest.mock import Mock

import pytest

from libecalc import dto
from libecalc.fixtures import YamlCase
from libecalc.presentation.flow_diagram.EcalcModelMapper import (
    EnergyModelFlowDiagram,
    FlowDiagram,
    Node,
    _filter_duplicate_flow_diagrams,
)


class TestEcalcModelMapper:
    @pytest.mark.snapshot
    def test_all_energy_usage_models(self, all_energy_usage_models_yaml: YamlCase, snapshot):
        model = all_energy_usage_models_yaml.get_yaml_model()
        actual_fd = EnergyModelFlowDiagram(
            energy_model=model, model_period=model.variables.period
        ).get_energy_flow_diagram()

        snapshot_name = "all_energy_usage_models_fde.json"
        snapshot.assert_match(
            json.dumps(actual_fd.model_dump(), sort_keys=True, indent=4, default=str), snapshot_name=snapshot_name
        )
        # To assure the correct end-time is used when filtering
        installation = next(node for node in actual_fd.nodes if node.id == "installation-MAIN_INSTALLATION")
        first_subdiagram = installation.subdiagram.pop(0)
        last_subdiagram = installation.subdiagram.pop(-1)
        assert first_subdiagram.end_date == datetime(2018, 1, 1)
        assert last_subdiagram.end_date == datetime(2021, 1, 1)

    @pytest.mark.snapshot
    def test_case_with_dates(self, installation_with_dates_dto_fd: dto.Asset, snapshot, energy_model_from_dto_factory):
        model = energy_model_from_dto_factory(installation_with_dates_dto_fd)
        actual_fd = EnergyModelFlowDiagram(
            energy_model=model, model_period=model.variables.period
        ).get_energy_flow_diagram()
        snapshot_name = "actual_fde.json"
        snapshot.assert_match(
            json.dumps(actual_fd.model_dump(), sort_keys=True, indent=4, default=str), snapshot_name=snapshot_name
        )

    def test_correct_duplicate_filtering(self):
        """Checking that all duplicates except last year returns only two out of 10 FDs.

        The change in nodes happens 2019-01-01 when we use a mock instead of an empty list.
        """
        duplicate_flow_diagrams: list[FlowDiagram] = [
            FlowDiagram(
                id="1",
                title="dummy",
                nodes=[] if year < 2019 else [Mock(Node)],
                edges=[],
                flows=[],
                start_date=datetime(year, 1, 1),
                end_date=datetime(year + 1, 1, 1),
            )
            for year in range(2010, 2020)
        ]

        filtered_diagrams = _filter_duplicate_flow_diagrams(duplicate_flow_diagrams)

        assert len(filtered_diagrams) == 2

        assert filtered_diagrams[0].start_date == datetime(2010, 1, 1)
        assert filtered_diagrams[0].end_date == datetime(2019, 1, 1)
        assert filtered_diagrams[-1].start_date == datetime(2019, 1, 1)
        assert filtered_diagrams[-1].end_date == datetime(2020, 1, 1)
