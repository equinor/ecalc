from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.dto import Asset
from libecalc.presentation.yaml.mappers.component_mapper import EcalcModelMapper
from libecalc.presentation.yaml.mappers.create_references import create_references
from libecalc.presentation.yaml.resource import Resources
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator

DEFAULT_START_TIME = datetime(1900, 1, 1)


def map_yaml_to_dto(configuration: YamlValidator, resources: Resources) -> Asset:
    # TODO: Replace configuration type with YamlValidator
    references = create_references(configuration, resources)
    target_period = Period(
        start=configuration.start or DEFAULT_START_TIME,
        end=configuration.end or datetime.max.replace(microsecond=0),
    )
    model_mapper = EcalcModelMapper(
        references=references,
        target_period=target_period,
    )
    return model_mapper.from_yaml_to_dto(configuration=configuration)
