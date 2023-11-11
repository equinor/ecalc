from datetime import datetime

from libecalc import dto
from libecalc.common.time_utils import Period
from libecalc.presentation.yaml.mappers.component_mapper import EcalcModelMapper
from libecalc.presentation.yaml.mappers.create_references import create_references
from libecalc.presentation.yaml.yaml_entities import Resources
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel

DEFAULT_START_TIME = datetime(1900, 1, 1)


def map_yaml_to_dto(configuration: PyYamlYamlModel, resources: Resources, name: str) -> dto.Asset:
    references = create_references(configuration, resources)
    target_period = Period(
        start=configuration.start or DEFAULT_START_TIME,
        end=configuration.end or datetime.max,
    )
    model_mapper = EcalcModelMapper(
        references=references,
        target_period=target_period,
    )
    return model_mapper.from_yaml_to_dto(configuration=configuration, name=name)
