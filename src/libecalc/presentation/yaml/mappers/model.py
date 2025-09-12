from collections.abc import Callable
from typing import Any, assert_never, cast

from pydantic import ValidationError

from libecalc.common.errors.exceptions import InvalidResourceException, ResourceFileMark
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.serializable_chart import ChartCurveDTO, SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.dto import EnergyModel
from libecalc.domain.process.value_objects.chart.compressor.compressor_chart_dto import CompressorChart
from libecalc.domain.process.value_objects.chart.generic import GenericChartFromDesignPoint, GenericChartFromInput
from libecalc.domain.resource import Resource, Resources
from libecalc.presentation.yaml.file_context import FileContext, FileMark
from libecalc.presentation.yaml.mappers.facility_input import (
    _create_pump_chart_variable_speed_dto_model_data,
    _create_pump_model_single_speed_dto_model_data,
    _create_tabulated_model,
)
from libecalc.presentation.yaml.mappers.utils import (
    YAML_UNIT_MAPPING,
    chart_curves_as_resource_to_dto_format,
    convert_efficiency_to_fraction,
    convert_head_to_joule_per_kg,
    convert_rate_to_am3_per_hour,
    get_single_speed_chart_data,
)
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.validation_errors import (
    Location,
    ModelValidationError,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlCompressorTabularModel,
    YamlFacilityModel,
    YamlGeneratorSetModel,
    YamlPumpChartSingleSpeed,
    YamlPumpChartVariableSpeed,
    YamlTabularModel,
)
from libecalc.presentation.yaml.yaml_types.models import (
    YamlCompressorChart,
    YamlCompressorWithTurbine,
    YamlConsumerModel,
    YamlTurbine,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlCurve,
    YamlGenericFromDesignPointChart,
    YamlGenericFromInputChart,
    YamlSingleSpeedChart,
    YamlVariableSpeedChart,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_trains import (
    YamlSimplifiedVariableSpeedCompressorTrain,
    YamlSingleSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlPressureControl
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import YamlCompositionFluidModel, YamlPredefinedFluidModel
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile


def _compressor_chart_mapper(model_config: YamlCompressorChart, resources: Resources) -> CompressorChart:
    chart_type = model_config.chart_type
    mapper = _compressor_chart_map.get(chart_type)
    if mapper is None:
        raise ValueError(f"Unknown chart type {chart_type}")
    return mapper(model_config, resources)


def _pressure_control_mapper(
    model_config: (
        YamlVariableSpeedCompressorTrain
        | YamlSingleSpeedCompressorTrain
        | YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures
    ),
) -> FixedSpeedPressureControl:
    return FixedSpeedPressureControl(model_config.pressure_control.value)


class InvalidChartResourceException(Exception):
    def __init__(self, message: str, file_mark: ResourceFileMark | None, resource_name: str):
        self.message = message
        self._resource_file_mark = file_mark
        self.resource_name = resource_name
        super().__init__(message)

    @property
    def location(self) -> Location:
        return Location([self.resource_name])

    @property
    def file_context(self):
        return FileContext(
            name=self.resource_name,
            start=self._file_mark,
        )

    @property
    def _file_mark(self) -> FileMark | None:
        if self._resource_file_mark is not None:
            return FileMark(
                line_number=self._resource_file_mark.row,
                column=self._resource_file_mark.column,
            )
        else:
            return None


def _single_speed_compressor_chart_mapper(
    model_config: YamlSingleSpeedChart, resources: Resources
) -> SingleSpeedChartDTO:
    curve_config = model_config.curve

    if isinstance(curve_config, YamlFile):
        resource_name = curve_config.file
        resource = resources.get(resource_name)
        if resource is None:
            raise ValueError(f"Resource '{resource_name}' not found for single speed chart.")

        try:
            chart_data = get_single_speed_chart_data(resource=resource)
        except InvalidResourceException as e:
            raise InvalidChartResourceException(
                message=str(e), file_mark=e.file_mark, resource_name=resource_name
            ) from e
        curve_data = {
            "speed": chart_data.speed,
            "rate": chart_data.rate,
            "head": chart_data.head,
            "efficiency": chart_data.efficiency,
        }
    else:
        curve_config = cast(YamlCurve, curve_config)  # type: ignore[redundant-cast]
        curve_data = {
            # Default to speed = 1 unless specified. This does not affect any calculations
            # but ensures we always have speed to handle charts in a generic way.
            "speed": curve_config.speed,
            "rate": curve_config.rate,
            "head": curve_config.head,
            "efficiency": curve_config.efficiency,
        }

    return SingleSpeedChartDTO(
        speed_rpm=curve_data["speed"],
        rate_actual_m3_hour=convert_rate_to_am3_per_hour(
            rate_values=curve_data["rate"], input_unit=YAML_UNIT_MAPPING[model_config.units.rate]
        ),
        polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
            head_values=curve_data["head"], input_unit=YAML_UNIT_MAPPING[model_config.units.head]
        ),
        efficiency_fraction=convert_efficiency_to_fraction(
            efficiency_values=curve_data["efficiency"],
            input_unit=YAML_UNIT_MAPPING[model_config.units.efficiency],
        ),
    )


def _variable_speed_compressor_chart_mapper(
    model_config: YamlVariableSpeedChart, resources: Resources
) -> VariableSpeedChartDTO:
    curve_config = model_config.curves

    if isinstance(curve_config, YamlFile):
        resource_name = curve_config.file
        resource = resources.get(resource_name)
        if resource is None:
            raise DomainValidationException(f"Resource '{resource_name}' not found for variable speed chart.")
        try:
            curves_data = chart_curves_as_resource_to_dto_format(resource=resource)
        except InvalidResourceException as e:
            raise InvalidChartResourceException(
                message=str(e), file_mark=e.file_mark, resource_name=resource_name
            ) from e
    else:
        curve_config = cast(list[YamlCurve], curve_config)  # type: ignore[redundant-cast]
        curves_data = curve_config  # Already a list of YamlCurve

    units = model_config.units

    curves: list[ChartCurveDTO] = [
        ChartCurveDTO(
            speed_rpm=curve.speed,
            rate_actual_m3_hour=convert_rate_to_am3_per_hour(
                rate_values=curve.rate,
                input_unit=YAML_UNIT_MAPPING[units.rate],
            ),
            polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
                head_values=curve.head, input_unit=YAML_UNIT_MAPPING[units.head]
            ),
            efficiency_fraction=convert_efficiency_to_fraction(
                efficiency_values=curve.efficiency,
                input_unit=YAML_UNIT_MAPPING[units.efficiency],
            ),
        )
        for curve in curves_data
    ]

    return VariableSpeedChartDTO(curves=curves)


def _generic_from_input_compressor_chart_mapper(
    model_config: YamlGenericFromInputChart, resources: Resources
) -> GenericChartFromInput:
    units = model_config.units

    polytropic_efficiency = model_config.polytropic_efficiency
    polytropic_efficiency_fraction = convert_efficiency_to_fraction(
        efficiency_values=[polytropic_efficiency],
        input_unit=YAML_UNIT_MAPPING[units.efficiency],
    )[0]

    return GenericChartFromInput(polytropic_efficiency_fraction=polytropic_efficiency_fraction)


def _generic_from_design_point_compressor_chart_mapper(
    model_config: YamlGenericFromDesignPointChart, resources: Resources
) -> GenericChartFromDesignPoint:
    design_rate = model_config.design_rate
    design_polytropic_head = model_config.design_head
    polytropic_efficiency = model_config.polytropic_efficiency

    units = model_config.units
    design_rate_actual_m3_per_hour = convert_rate_to_am3_per_hour(
        rate_values=[design_rate], input_unit=YAML_UNIT_MAPPING[units.rate]
    )[0]
    design_polytropic_head_joule_per_kg = convert_head_to_joule_per_kg(
        head_values=[design_polytropic_head], input_unit=YAML_UNIT_MAPPING[units.head]
    )[0]
    polytropic_efficiency_fraction = convert_efficiency_to_fraction(
        efficiency_values=[polytropic_efficiency],
        input_unit=YAML_UNIT_MAPPING[units.efficiency],
    )[0]

    return GenericChartFromDesignPoint(
        polytropic_efficiency_fraction=polytropic_efficiency_fraction,
        design_rate_actual_m3_per_hour=design_rate_actual_m3_per_hour,
        design_polytropic_head_J_per_kg=design_polytropic_head_joule_per_kg,
    )


_compressor_chart_map: dict[str, Callable[[Any, Resources], CompressorChart]] = {
    EcalcYamlKeywords.consumer_chart_type_variable_speed: _variable_speed_compressor_chart_mapper,
    EcalcYamlKeywords.consumer_chart_type_generic_from_input: _generic_from_input_compressor_chart_mapper,
    EcalcYamlKeywords.consumer_chart_type_generic_from_design_point: _generic_from_design_point_compressor_chart_mapper,
    EcalcYamlKeywords.consumer_chart_type_single_speed: _single_speed_compressor_chart_mapper,
}


def map_yaml_to_fixed_speed_pressure_control(yaml_control: YamlPressureControl) -> FixedSpeedPressureControl:
    mapping = {
        YamlPressureControl.UPSTREAM_CHOKE: FixedSpeedPressureControl.UPSTREAM_CHOKE,
        YamlPressureControl.DOWNSTREAM_CHOKE: FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        YamlPressureControl.INDIVIDUAL_ASV_PRESSURE: FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
        YamlPressureControl.INDIVIDUAL_ASV_RATE: FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE,
        YamlPressureControl.COMMON_ASV: FixedSpeedPressureControl.COMMON_ASV,
    }
    return mapping[yaml_control]


ModelType = YamlConsumerModel | YamlFacilityModel


class ModelMapper:
    def __init__(self, resources: Resources, configuration: YamlValidator):
        self.__resources = resources
        self.__configuration = configuration

        self._yaml_path: YamlPath | None = None
        self._model: ModelType | None = None

    def _create_error(self, message: str, key: str | None = None):
        assert self._model is not None and self._yaml_path is not None
        location_keys = [*self._yaml_path.keys[:-1], self._model.name]  # Replace index with name
        if key is not None:
            key_path = self._yaml_path.append(key)
            location_keys.append(key)
        else:
            key_path = self._yaml_path

        file_context = self.__configuration.get_file_context(key_path.keys)
        return ModelValidationError(
            message=message,
            location=Location(keys=location_keys),
            name=self._model.name,
            file_context=file_context,
        )

    def _get_resource(self, resource_name: str) -> Resource:
        resource = self.__resources.get(resource_name)
        if resource is None:
            raise ModelValidationException(
                errors=[self._create_error(message=f"Unable to find resource '{resource_name}'", key="FILE")]
            )
        return resource

    def create_model(self, model: ModelType, input_models: dict[str, Any], resources: Resources):
        if isinstance(
            model,
            YamlPredefinedFluidModel
            | YamlCompositionFluidModel
            | YamlSingleSpeedChart
            | YamlVariableSpeedChart
            | YamlGenericFromInputChart
            | YamlGenericFromDesignPointChart
            | YamlSimplifiedVariableSpeedCompressorTrain
            | YamlVariableSpeedCompressorTrain
            | YamlSingleSpeedCompressorTrain
            | YamlTurbine
            | YamlCompressorWithTurbine
            | YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures
            | YamlCompressorTabularModel
            | YamlGeneratorSetModel,
        ):
            return None
        elif isinstance(model, YamlTabularModel):
            resource = self._get_resource(model.file)
            return _create_tabulated_model(resource=resource, facility_data=model)
        elif isinstance(model, YamlPumpChartSingleSpeed):
            resource = self._get_resource(model.file)
            return _create_pump_model_single_speed_dto_model_data(resource=resource, facility_data=model)
        elif isinstance(model, YamlPumpChartVariableSpeed):
            resource = self._get_resource(model.file)
            return _create_pump_chart_variable_speed_dto_model_data(resource=resource, facility_data=model)
        else:
            assert_never(model)

    def from_yaml_to_dto(
        self, model_config: ModelType, input_models: dict[str, Any], yaml_path: YamlPath
    ) -> EnergyModel:
        self._yaml_path = yaml_path
        self._model = model_config

        try:
            model_data = self.create_model(model=model_config, input_models=input_models, resources=self.__resources)
            return model_data
        except ValidationError as ve:
            raise ModelValidationException.from_pydantic(
                validation_error=ve, file_context=self.__configuration.get_file_context(yaml_path.keys)
            ) from ve
        except DomainValidationException as vve:
            raise ModelValidationException(errors=[self._create_error(str(vve))]) from vve
        except ValueError as e:
            raise ModelValidationException(errors=[self._create_error(str(e), key=None)]) from e
        except InvalidResourceException as e:
            if e.file_mark is not None:
                start_file_mark = FileMark(
                    line_number=e.file_mark.row,
                    column=e.file_mark.column,
                )
            else:
                start_file_mark = None

            resource_name = model_config.file if hasattr(model_config, "file") else ""

            file_context = FileContext(
                name=resource_name,
                start=start_file_mark,
            )

            raise ModelValidationException(
                errors=[
                    ModelValidationError(
                        message=str(e),
                        location=Location([resource_name]),
                        file_context=file_context,
                    ),
                ],
            ) from e
        except InvalidChartResourceException as e:
            raise ModelValidationException(
                errors=[
                    ModelValidationError(
                        message=str(e),
                        location=e.location,
                        file_context=e.file_context,
                    ),
                ],
            ) from e
