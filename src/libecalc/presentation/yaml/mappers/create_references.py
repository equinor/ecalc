from collections.abc import Iterable
from typing import Protocol

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.logger import logger
from libecalc.domain.process.dto import EnergyModel
from libecalc.domain.resource import Resources
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.mappers.facility_input import FacilityInputMapper
from libecalc.presentation.yaml.mappers.fuel_and_emission_mapper import FuelMapper
from libecalc.presentation.yaml.mappers.model import ModelMapper
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel


def create_references(configuration: YamlValidator, resources: Resources) -> ReferenceService:
    """Create references-lookup used throughout the yaml.

    :param resources: list of resources containing data for the FILE reference in facility input
    :param configuration: dict representation of yaml input
    :return: References: mapping from reference to data for several categories
    """
    facility_input_mapper = FacilityInputMapper(resources=resources)
    facility_inputs_from_files = {
        facility_input.name: facility_input_mapper.from_yaml_to_dto(facility_input)
        for facility_input in configuration.facility_inputs
    }
    models = create_model_references(
        models_yaml_config=configuration.models,
        facility_inputs=facility_inputs_from_files,
        resources=resources,
    )

    fuel_types = {fuel_data.name: FuelMapper.from_yaml_to_dto(fuel_data) for fuel_data in configuration.fuel_types}

    return References(
        models=models,
        fuel_types=fuel_types,
    )


def create_model_references(
    models_yaml_config: Iterable[YamlConsumerModel],
    facility_inputs: dict[str, EnergyModel],
    resources: Resources,
):
    sorted_models = _sort_models(models_yaml_config)

    models_map = facility_inputs
    model_mapper = ModelMapper(resources=resources)

    for model in sorted_models:
        model_reference = model.name
        models_map[model_reference] = model_mapper.from_yaml_to_dto(model, models_map)

    return models_map


# Some models are referenced by other models, for example a compressor model will reference compressor chart models
# and fluid models. A compressor with turbine model will reference a compressor model and a turbine model
# In the mapping, the references are replaced with the parsed referenced model, hence they need to be parsed in an order
# which ensures all the references has been parsed up front.
_model_parsing_order_map = {
    EcalcYamlKeywords.models_type_fluid: 0,
    EcalcYamlKeywords.models_type_compressor_chart: 0,
    EcalcYamlKeywords.models_type_compressor_train_simplified: 1,
    EcalcYamlKeywords.models_type_compressor_train_variable_speed: 1,
    EcalcYamlKeywords.models_type_compressor_train_single_speed: 1,
    EcalcYamlKeywords.models_type_compressor_train_variable_speed_multiple_streams_and_pressures: 1,
    EcalcYamlKeywords.models_type_turbine: 0,
    EcalcYamlKeywords.models_type_compressor_with_turbine: 2,
}


class SortableModel(Protocol):
    name: str
    type: str


def _model_parsing_order(model: SortableModel) -> int:
    model_type = model.type
    try:
        return _model_parsing_order_map[model_type]
    except KeyError as e:
        msg = f"{model.name}:\nUnknown model type {model_type}."
        logger.exception(msg + f": {e}")
        raise EcalcError(title="Invalid model", message=msg) from e


def _sort_models(models: Iterable[SortableModel]):
    return sorted(models, key=_model_parsing_order)
