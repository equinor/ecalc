import json
from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.domain.energy import EnergyModel
from libecalc.fixtures import YamlCase
from libecalc.presentation.flow_diagram.energy_model_flow_diagram import (
    EnergyModelFlowDiagram,
)


class TestEcalcModelMapper:
    @pytest.mark.snapshot
    @pytest.mark.usefixtures("patch_uuid")
    def test_all_energy_usage_models(self, all_energy_usage_models_yaml: YamlCase, snapshot):
        model = all_energy_usage_models_yaml.get_yaml_model().validate_for_run()
        energy_model = model.get_energy_model()
        actual_fd = EnergyModelFlowDiagram(
            energy_model=energy_model, model_period=model.variables.period
        ).get_energy_flow_diagram()

        snapshot_name = "all_energy_usage_models_fde.json"
        snapshot.assert_match(
            json.dumps(actual_fd.model_dump(), sort_keys=True, indent=4, default=str), snapshot_name=snapshot_name
        )
        main_installation_id = next(
            installation.get_id()
            for installation in model.get_installations()
            if installation.get_name() == "MAIN_INSTALLATION"
        )
        # To assure the correct end-time is used when filtering
        installation = next(node for node in actual_fd.nodes if node.id == str(main_installation_id))

        assert len(installation.subdiagram) == 1

        first_subdiagram = installation.subdiagram.pop(0)
        assert first_subdiagram.start_date == datetime(2017, 1, 1)
        assert first_subdiagram.end_date == datetime(2021, 1, 1)

    @pytest.mark.snapshot
    def test_case_with_dates(
        self,
        dated_installation_energy_model: EnergyModel,
        snapshot,
    ):
        target_period = Period(start=datetime(1900, 1, 1), end=datetime(2021, 1, 1))
        actual_fd = EnergyModelFlowDiagram(
            energy_model=dated_installation_energy_model,
            model_period=target_period,
        ).get_energy_flow_diagram()
        snapshot_name = "actual_fde.json"
        snapshot.assert_match(
            json.dumps(actual_fd.model_dump(), sort_keys=True, indent=4, default=str), snapshot_name=snapshot_name
        )
