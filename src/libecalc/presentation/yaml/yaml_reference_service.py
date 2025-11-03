import logging
from collections.abc import Iterable
from typing import Any, get_args

from libecalc.common.errors.exceptions import EcalcError
from libecalc.presentation.yaml.domain.reference_service import (
    InvalidReferenceException,
    ReferenceService,
    YamlCompressorModel,
)
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlFacilityModel,
    YamlGeneratorSetModel,
    YamlPumpChartSingleSpeed,
    YamlPumpChartVariableSpeed,
    YamlTabularModel,
)
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model_type import YamlFacilityModelType
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import (
    YamlCompressorChart,
    YamlConsumerModel,
    YamlFluidModel,
    YamlTurbine,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType

logger = logging.getLogger(__name__)

YamlModel = YamlConsumerModel | YamlFacilityModel

ReferenceType = YamlModel | YamlFuelType

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


def _model_parsing_order(model: YamlModel) -> int:
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


def _sort_models(models: Iterable[YamlModel]):
    return sorted(models, key=_model_parsing_order)


Reference = str


class YamlReferenceService(ReferenceService):
    def __init__(
        self,
        configuration: YamlValidator,
    ):
        facility_inputs_path = YamlPath(keys=("FACILITY_INPUTS",))
        references: dict[Reference, ReferenceType] = {}
        reference_yaml_context: dict[Reference, YamlPath] = {}
        for index, facility_input in enumerate(configuration.facility_inputs):
            facility_input_path = facility_inputs_path.append(index)
            references[facility_input.name] = facility_input
            reference_yaml_context[facility_input.name] = facility_input_path

        models_yaml_path = YamlPath(keys=("MODELS",))
        for model_index, model in enumerate(configuration.models):
            model_yaml_path = models_yaml_path.append(model_index)
            references[model.name] = model
            reference_yaml_context[model.name] = model_yaml_path

        fuel_types_path = YamlPath(keys=("FUEL_TYPES",))
        for fuel_type_index, fuel_type in enumerate(configuration.fuel_types):
            fuel_type_path = fuel_types_path.append(fuel_type_index)
            references[fuel_type.name] = fuel_type
            reference_yaml_context[fuel_type.name] = fuel_type_path

        self._references = references
        self._references_yaml_context = reference_yaml_context

    def get_yaml_path(self, reference: str) -> YamlPath:
        return self._references_yaml_context[reference]

    def get_fluid(self, reference: str) -> YamlFluidModel:
        model = self._resolve_yaml_reference(reference, "fluid model")
        if not isinstance(model, get_args(get_args(YamlFluidModel)[0])):
            raise InvalidReferenceException("fluid model", reference)
        return model

    def get_turbine(self, reference: str) -> YamlTurbine:
        model = self._resolve_yaml_reference(reference, "turbine model")
        if not isinstance(model, YamlTurbine):
            raise InvalidReferenceException("turbine model", reference)
        return model

    def get_compressor_chart(self, reference: str) -> YamlCompressorChart:
        model = self._resolve_yaml_reference(reference, "compressor chart")
        if not isinstance(model, get_args(get_args(YamlCompressorChart)[0])):
            raise InvalidReferenceException("compressor chart", reference)
        return model

    def get_fuel_reference(self, reference: str) -> YamlFuelType:
        fuel = self._resolve_yaml_reference(reference, "fuel")
        if not isinstance(fuel, YamlFuelType):
            raise InvalidReferenceException("fuel", reference, self._references.keys())
        return fuel

    def _resolve_yaml_reference(self, reference: str, reference_type_name: str) -> Any:
        try:
            return self._references[reference]
        except (KeyError, TypeError) as e:
            # KeyError: key does not exist
            # TypeError: models is None
            raise InvalidReferenceException(reference_type_name, reference, self._references.keys()) from e

    def get_generator_set_model(self, reference: str) -> YamlGeneratorSetModel:
        model = self._resolve_yaml_reference(reference, "generator set model")
        if not isinstance(model, YamlGeneratorSetModel):
            raise InvalidReferenceException("generator set model", reference)
        return model

    def get_compressor_model(self, reference: str) -> YamlCompressorModel:
        model = self._resolve_yaml_reference(reference, "compressor model")
        if not isinstance(model, YamlCompressorModel):
            raise InvalidReferenceException("compressor model", reference)
        return model

    def get_pump_model(self, reference: str) -> YamlPumpChartSingleSpeed | YamlPumpChartVariableSpeed:
        model = self._resolve_yaml_reference(reference, "pump model")
        if not isinstance(model, YamlPumpChartSingleSpeed | YamlPumpChartVariableSpeed):
            raise InvalidReferenceException("pump model", reference)
        return model

    def get_tabulated_model(self, reference: str) -> YamlTabularModel:
        model = self._resolve_yaml_reference(reference, "tabulated")
        if not isinstance(model, YamlTabularModel):
            raise InvalidReferenceException("tabulated", reference)
        return model
