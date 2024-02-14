from typing import Dict, List

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.logger import logger
from libecalc.common.string.string_utils import get_duplicates
from libecalc.presentation.yaml.mappers.facility_input import FacilityInputMapper
from libecalc.presentation.yaml.mappers.fuel_and_emission_mapper import FuelMapper
from libecalc.presentation.yaml.mappers.model import ModelMapper
from libecalc.presentation.yaml.yaml_entities import References, Resources
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel


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

    duplicated_fuel_names = get_duplicates(
        [fuel_data.get(EcalcYamlKeywords.name) for fuel_data in configuration.fuel_types]
    )

    if len(duplicated_fuel_names) > 0:
        raise EcalcError(
            title="Duplicate names",
            message="Fuel type names must be unique across installations."
            f" Duplicated names are: {', '.join(duplicated_fuel_names)}",
        )

    fuel_types_emissions = [list(fuel_data[EcalcYamlKeywords.emissions]) for fuel_data in configuration.fuel_types]

    # Check each fuel for duplicated emissions
    duplicated_emissions = []
    for emissions in fuel_types_emissions:
        duplicated_emissions.append(get_duplicates([emission.get(EcalcYamlKeywords.name) for emission in emissions]))

    duplicated_emissions_names = ",".join(name for string in duplicated_emissions for name in string if len(string) > 0)

    if len(duplicated_emissions_names) > 0:
        raise EcalcError(
            title="Duplicate names",
            message="Emission names must be unique for each fuel type. "
            f"Duplicated names are: {duplicated_emissions_names}",
        )

    fuel_types = {
        fuel_data.get(EcalcYamlKeywords.name): FuelMapper.from_yaml_to_dto(fuel_data)
        for fuel_data in configuration.fuel_types
    }

    consumers_installations = []
    for installation in configuration.installations:
        if installation.get(EcalcYamlKeywords.generator_sets) is not None:
            consumers_installations.append(
                [
                    consumer
                    for consumers in installation[EcalcYamlKeywords.generator_sets]
                    for consumer in consumers[EcalcYamlKeywords.consumers]
                ]
            )

        if installation.get(EcalcYamlKeywords.fuel_consumers) is not None:
            consumers_installations.append(list(installation[EcalcYamlKeywords.fuel_consumers]))

    check_multiple_energy_models(consumers_installations)

    return References(
        models=models,
        fuel_types=fuel_types,
    )


def check_multiple_energy_models(consumers_installations: List[List[Dict]]):
    """
    Check for different energy model types within one consumer.
    Raises value error if different energy model types found within one consumer.

    Args:
        consumers_installations (List[List[Dict]]): List of consumers per installation

    Returns:
        None
    """
    for consumers in consumers_installations:
        for consumer in consumers:
            energy_models = []

            # Check if key exists: ENERGY_USAGE_MODEL.
            # Consumer system v2 has different structure/naming: test fails when looking for key ENERGY_USAGE_MODEL
            if EcalcYamlKeywords.energy_usage_model in consumer:
                for model in consumer[EcalcYamlKeywords.energy_usage_model].values():
                    if isinstance(model, dict):
                        for key, value in model.items():
                            if key == EcalcYamlKeywords.type and value not in energy_models:
                                energy_models.append(value)
            if len(energy_models) > 1:
                raise EcalcError(
                    title="Invalid model",
                    message="Energy model type cannot change over time within a single consumer."
                    f" The model type is changed for {consumer[EcalcYamlKeywords.name]}: {energy_models}",
                )


def create_model_references(models_yaml_config, facility_inputs: Dict, resources: Resources):
    sorted_models = _sort_models(models_yaml_config)

    models_map = facility_inputs
    model_mapper = ModelMapper(resources=resources)

    for model in sorted_models:
        model_reference = model.get(EcalcYamlKeywords.name)
        if model_reference in models_map:
            raise EcalcError(
                title="Duplicate reference",
                message=f"The model '{model_reference}' is defined multiple times",
            )
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
        lines_reference = f"Check lines {model.start_mark.line} to {model.end_mark.line} in Yaml-file."
        none_msg = f"Have you remembered to include the {EcalcYamlKeywords.type} keyword?" if model_type is None else ""
        msg = f"{model[EcalcYamlKeywords.name]}:\nUnknown model type {model_type}. {none_msg}\n{lines_reference}"

        logger.exception(msg + f": {e}")
        raise EcalcError(title="Invalid model", message=msg) from e


def _sort_models(models):
    return sorted(models, key=_model_parsing_order)
