import logging
from collections.abc import Iterable
from typing import Any, get_args

from libecalc.common.errors.exceptions import EcalcError
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import TabularEnergyFunction
from libecalc.domain.process.compressor.core import CompressorModel, create_compressor_model
from libecalc.domain.process.compressor.dto.model_types import CompressorModelTypes
from libecalc.domain.process.dto import EnergyModel
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.resource import Resources
from libecalc.dto import FuelType
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException, ReferenceService
from libecalc.presentation.yaml.mappers.fuel_and_emission_mapper import FuelMapper
from libecalc.presentation.yaml.mappers.model import ModelMapper, ModelType
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModelType
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType

logger = logging.getLogger(__name__)


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


def _model_parsing_order(model: ModelType) -> int:
    model_type = model.type
    try:
        if isinstance(model_type, YamlFacilityModelType):
            return 0
        else:
            assert isinstance(model_type, YamlModelType)
            return _model_parsing_order_map[model_type]
    except KeyError as e:
        msg = f"{model.name}:\nUnknown model type {model_type}."
        logger.exception(msg + f": {e}")
        raise EcalcError(title="Invalid model", message=msg) from e


def _sort_models(models: Iterable[ModelType]):
    return sorted(models, key=_model_parsing_order)


FacilityModelReference = str


class YamlReferenceService(ReferenceService):
    def __init__(
        self,
        configuration: YamlValidator,
        resources: Resources,
    ):
        facility_inputs_path = YamlPath(keys=("FACILITY_INPUTS",))
        model_references: dict[FacilityModelReference, ModelType] = {}
        model_yaml_context: dict[FacilityModelReference, YamlPath] = {}
        for index, facility_input in enumerate(configuration.facility_inputs):
            facility_input_path = facility_inputs_path.append(index)
            model_references[facility_input.name] = facility_input
            model_yaml_context[facility_input.name] = facility_input_path

        models_yaml_path = YamlPath(keys=("MODELS",))
        for model_index, model in enumerate(configuration.models):
            model_yaml_path = models_yaml_path.append(model_index)
            model_references[model.name] = model
            model_yaml_context[model.name] = model_yaml_path

        model_mapper = ModelMapper(resources=resources, configuration=configuration)

        parsed_model_references: dict[FacilityModelReference, Any] = {}
        for model in _sort_models(model_references.values()):
            model_yaml_path = model_yaml_context[model.name]
            parsed_model_references[model.name] = model_mapper.from_yaml_to_dto(
                model, parsed_model_references, yaml_path=model_yaml_path
            )

        fuel_mapper = FuelMapper(configuration)

        fuel_types = {
            fuel_data.name: fuel_mapper.from_yaml_to_dto(fuel_data, fuel_index)
            for fuel_index, fuel_data in enumerate(configuration.fuel_types)
        }
        self._models = parsed_model_references
        self._fuel_types = fuel_types

    def get_fuel_reference(self, reference: str) -> FuelType:
        try:
            return self._fuel_types[reference]
        except (KeyError, TypeError) as e:
            # KeyError: key does not exist
            # TypeError: fuel_types is None
            raise InvalidReferenceException("fuel", reference, self._fuel_types.keys()) from e

    def _get_model_reference(self, reference: str, reference_type_name: str) -> EnergyModel:
        try:
            return self._models[reference]
        except (KeyError, TypeError) as e:
            # KeyError: key does not exist
            # TypeError: models is None
            raise InvalidReferenceException(reference_type_name, reference, self._models.keys()) from e

    def get_generator_set_model(self, reference: str) -> GeneratorSetModel:
        model = self._get_model_reference(reference, "generator set model")
        if not isinstance(model, GeneratorSetModel):
            raise InvalidReferenceException("generator set model", reference)
        return model

    def get_compressor_model(self, reference: str) -> CompressorModel:
        model = self._get_model_reference(reference, "compressor model")
        if not isinstance(model, get_args(CompressorModelTypes)):
            raise InvalidReferenceException("compressor model", reference)
        return create_compressor_model(model)

    def get_pump_model(self, reference: str) -> PumpModel:
        model = self._get_model_reference(reference, "compressor model")
        if not isinstance(model, PumpModel):
            raise InvalidReferenceException("pump model", reference)
        return model

    def get_tabulated_model(self, reference: str) -> TabularEnergyFunction:
        model = self._get_model_reference(reference, "tabulated")
        if not isinstance(model, TabularEnergyFunction):
            raise InvalidReferenceException("tabulated", reference)
        return model
