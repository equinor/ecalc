from typing import Dict

from libecalc.common.logger import logger
from libecalc.input.mappers.facility_input import FacilityInputMapper
from libecalc.input.mappers.fuel_and_emission_mapper import FuelMapper
from libecalc.input.mappers.model import ModelMapper
from libecalc.input.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.input.yaml_entities import References, Resources
from libecalc.input.yaml_keywords import EcalcYamlKeywords


def create_references(configuration: PyYamlYamlModel, resources: Resources) -> References:
    """Create references-lookup used throughout the yaml.

    :param resources: list of resources containing data for the FILE reference in facility input
    :param configuration: dict representation of yaml input
    :return: References: mapping from reference to data for several categories
    """
    facility_input_mapper = FacilityInputMapper(resources=resources)
    facility_inputs_from_files = {
        facility_input.get(EcalcYamlKeywords.name): facility_input_mapper.from_yaml_to_dto(facility_input)
        for facility_input in configuration.facility_inputs
    }
    models = create_model_references(
        models_yaml_config=configuration.models,
        facility_inputs=facility_inputs_from_files,
        resources=resources,
    )
    fuel_types = {
        fuel_data.get(EcalcYamlKeywords.name): FuelMapper.from_yaml_to_dto(fuel_data)
        for fuel_data in configuration.fuel_types
    }
    return References(
        models=models,
        fuel_types=fuel_types,
    )


def create_model_references(models_yaml_config, facility_inputs: Dict, resources: Resources):
    sorted_models = _sort_models(models_yaml_config)

    models_map = facility_inputs
    model_mapper = ModelMapper(resources=resources)

    for model in sorted_models:
        model_reference = model.get(EcalcYamlKeywords.name)
        if model_reference in models_map:
            raise ValueError("Duplicated references not supported.")
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


def _model_parsing_order(model) -> int:
    model_type = model.get(EcalcYamlKeywords.type)
    try:
        return _model_parsing_order_map[model_type]
    except KeyError as e:
        msg = f"Unknown model type {model_type}"
        logger.exception(msg + f": {e}")
        raise ValueError(msg) from e


def _sort_models(models):
    return sorted(models, key=_model_parsing_order)
