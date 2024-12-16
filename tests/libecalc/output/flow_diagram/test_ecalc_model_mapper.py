import json
from datetime import datetime

import pytest

from libecalc.domain.infrastructure import Asset
from libecalc.fixtures import YamlCase
from libecalc.presentation.flow_diagram.energy_model_flow_diagram import (
    EnergyModelFlowDiagram,
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
        installation = next(node for node in actual_fd.nodes if node.id == "MAIN_INSTALLATION")

        assert len(installation.subdiagram) == 1

        first_subdiagram = installation.subdiagram.pop(0)
        assert first_subdiagram.start_date == datetime(2017, 1, 1)
        assert first_subdiagram.end_date == datetime(2021, 1, 1)

    @pytest.mark.snapshot
    def test_case_with_dates(self, installation_with_dates_dto_fd: Asset, snapshot, energy_model_from_dto_factory):
        model = energy_model_from_dto_factory(installation_with_dates_dto_fd)
        actual_fd = EnergyModelFlowDiagram(
            energy_model=model, model_period=list(installation_with_dates_dto_fd.installations[0].regularity.keys())[0]
        ).get_energy_flow_diagram()
        snapshot_name = "actual_fde.json"
        snapshot.assert_match(
            json.dumps(actual_fd.model_dump(), sort_keys=True, indent=4, default=str), snapshot_name=snapshot_name
        )
