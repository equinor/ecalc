from datetime import datetime
from pathlib import Path
from typing import Optional

from libecalc import dto
from libecalc.dto import VariablesMap
from libecalc.fixtures import DTOCase, YamlCase
from libecalc.presentation.yaml.mappers import map_yaml_to_variables
from libecalc.presentation.yaml.parse_input import map_yaml_to_dto
from libecalc.presentation.yaml.yaml_entities import Resources, ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel


def parse_input(
    main_yaml: ResourceStream,
    resources: Resources = None,
    base_dir: Optional[Path] = None,
) -> (dto.Asset, Optional[VariablesMap]):
    """The stream on top here does NOT expect timeseries as a part of the yaml, only
    facility_types, models, installations, start_time, end_time. Timeseries are handled
    separately.

    NOTE: This function is a "work-in-progress", and currently only used in order to
    bootstrap tests and test current functionality in common.
    :param base_dir:
    :param main_yaml:
    :param resources:
    :return:
    """
    configuration: PyYamlYamlModel = PyYamlYamlModel.read(main_yaml=main_yaml, enable_include=True, base_dir=base_dir)
    model_dto = map_yaml_to_dto(
        configuration,
        resources,
        name=Path(main_yaml.name).stem,
        variables_map=dto.VariablesMap(time_vector=[datetime(1900, 1, 1)], variables={}),
    )

    variables = map_yaml_to_variables(configuration, resources, result_options=dto.ResultOptions())

    return (
        model_dto,
        variables,
    )


class TestParseYaml:
    def test_parse_input_with_all_energy_usage_models(
        self, all_energy_usage_models_yaml: YamlCase, all_energy_usage_models_dto: DTOCase
    ):
        model_dto, variables = parse_input(
            ResourceStream(stream=all_energy_usage_models_yaml.main_file, name="all_energy_usage_models.yaml"),
            resources=all_energy_usage_models_yaml.resources,
        )

        assert model_dto.dict() == all_energy_usage_models_dto.ecalc_model.dict()
        assert variables == all_energy_usage_models_dto.variables

    def test_parse_input_with_consumer_system_v2(self, consumer_system_v2_yaml, consumer_system_v2_dto_fixture):
        model_dto, variables = parse_input(
            ResourceStream(stream=consumer_system_v2_yaml.main_file, name="consumer_system_v2.yaml"),
            resources=consumer_system_v2_yaml.resources,
        )

        assert model_dto.dict() == consumer_system_v2_dto_fixture.ecalc_model.dict()
        assert variables == consumer_system_v2_dto_fixture.variables
