from collections.abc import Iterable

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.logger import logger
from libecalc.domain.resource import Resources
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.mappers.facility_input import FacilityInputMapper
from libecalc.presentation.yaml.mappers.fuel_and_emission_mapper import FuelMapper
from libecalc.presentation.yaml.mappers.model import ModelMapper
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType


def create_references(configuration: YamlValidator, resources: Resources) -> ReferenceService:
    """Create references-lookup used throughout the yaml.

    :param resources: list of resources containing data for the FILE reference in facility input
    :param configuration: dict representation of yaml input
    :return: References: mapping from reference to data for several categories
    """
    facility_input_mapper = FacilityInputMapper(resources=resources)
    model_references = {
        facility_input.name: facility_input_mapper.from_yaml_to_dto(facility_input)
        for facility_input in configuration.facility_inputs
    }

    model_mapper = ModelMapper(resources=resources, configuration=configuration)
    models_yaml_path = YamlPath(keys=("MODELS",))
    model_name_index_map = {model.name: model_index for model_index, model in enumerate(configuration.models)}

    for model in _sort_models(configuration.models):
        model_reference = model.name
        model_yaml_path = models_yaml_path.append(model_name_index_map[model_reference])
        model_references[model_reference] = model_mapper.from_yaml_to_dto(
            model, model_references, yaml_path=model_yaml_path
        )

    fuel_mapper = FuelMapper(configuration)

    fuel_types = {
        fuel_data.name: fuel_mapper.from_yaml_to_dto(fuel_data, fuel_index)
        for fuel_index, fuel_data in enumerate(configuration.fuel_types)
    }

    return References(
        models=model_references,
        fuel_types=fuel_types,
    )


# Some models are referenced by other models, for example a compressor model will reference compressor chart models
# and fluid models. A compressor with turbine model will reference a compressor model and a turbine model
# In the mapping, the references are replaced with the parsed referenced model, hence they need to be parsed in an order
# which ensures all the references has been parsed up front.
_model_parsing_order_map = {
    YamlModelType.FLUID: 0,
    YamlModelType.COMPRESSOR_CHART: 0,
    YamlModelType.TURBINE: 0,
    YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN: 1,
    YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN: 1,
    YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN: 1,
    YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES: 1,
    YamlModelType.COMPRESSOR_WITH_TURBINE: 2,
}


def _model_parsing_order(model: YamlConsumerModel) -> int:
    model_type = model.type
    try:
        return _model_parsing_order_map[model_type]
    except KeyError as e:
        msg = f"{model.name}:\nUnknown model type {model_type}."
        logger.exception(msg + f": {e}")
        raise EcalcError(title="Invalid model", message=msg) from e


def _sort_models(models: Iterable[YamlConsumerModel]):
    return sorted(models, key=_model_parsing_order)
