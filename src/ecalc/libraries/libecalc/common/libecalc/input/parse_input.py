from datetime import datetime

from libecalc import dto
from libecalc.common.time_utils import Period
from libecalc.input.mappers.component_mapper import EcalcModelMapper
from libecalc.input.mappers.create_references import create_references
from libecalc.input.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.input.yaml_entities import Resources

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
