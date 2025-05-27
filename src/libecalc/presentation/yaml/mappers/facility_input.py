from typing import Union

from pydantic import ValidationError

from libecalc.common.chart_type import ChartType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.common.serializable_chart import ChartCurveDTO, SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.process.compressor.dto import CompressorSampled as CompressorTrainSampledDTO
from libecalc.domain.process.dto import EnergyModel, TabulatedData
from libecalc.domain.process.pump.pump import PumpModelDTO
from libecalc.domain.resource import Resource, Resources
from libecalc.presentation.yaml.mappers.energy_model_factory import EnergyModelFactory
from libecalc.presentation.yaml.mappers.utils import (
    YAML_UNIT_MAPPING,
    chart_curves_as_resource_to_dto_format,
    convert_efficiency_to_fraction,
    convert_head_to_joule_per_kg,
    convert_rate_to_am3_per_hour,
    get_single_speed_chart_data,
)
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
    DumpFlowStyle,
    ValidationValueError,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlCompressorTabularModel,
    YamlFacilityAdjustment,
    YamlFacilityModel,
    YamlFacilityModelBase,
    YamlGeneratorSetModel,
    YamlPumpChartSingleSpeed,
    YamlPumpChartVariableSpeed,
)

# Used here to make pydantic understand which object to instantiate.
EnergyModelUnionType = Union[GeneratorSetModel, TabulatedData, CompressorTrainSampledDTO]

energy_model_type_map = {
    EcalcYamlKeywords.facility_type_electricity2fuel: EnergyModelType.GENERATOR_SET_SAMPLED,
    EcalcYamlKeywords.facility_type_pump_chart_single_speed: ChartType.SINGLE_SPEED,
    EcalcYamlKeywords.facility_type_pump_chart_variable_speed: ChartType.VARIABLE_SPEED,
    EcalcYamlKeywords.facility_type_compressor_tabular: EnergyModelType.COMPRESSOR_SAMPLED,
    EcalcYamlKeywords.facility_type_tabular: EnergyModelType.TABULATED,
}

PUMP_CHART_TYPES = [ChartType.SINGLE_SPEED, ChartType.VARIABLE_SPEED]


def _get_adjustment_constant(data: YamlFacilityModelBase) -> float:
    if data.adjustment is None:
        return YamlFacilityAdjustment().constant
    return data.adjustment.constant


def _get_adjustment_factor(data: YamlFacilityModelBase) -> float:
    if data.adjustment is None:
        return YamlFacilityAdjustment().factor
    return data.adjustment.factor


def _get_column_or_none(resource: Resource, header: str) -> list[float | int | str] | None:
    try:
        return resource.get_column(header)
    except InvalidResourceException:
        return None


def _create_compressor_train_sampled_dto_model_data(
    resource: Resource, facility_data: YamlCompressorTabularModel, **kwargs
) -> CompressorTrainSampledDTO:
    # kwargs just to allow this to be used with _default_facility_to_dto_model_data which needs type until we have
    # replaced _default_facility_to_dto_model_data and have separate functions for all types
    rate_header = EcalcYamlKeywords.consumer_function_rate
    suction_pressure_header = EcalcYamlKeywords.consumer_function_suction_pressure
    discharge_pressure_header = EcalcYamlKeywords.consumer_function_discharge_pressure
    power_header = EcalcYamlKeywords.consumer_tabular_power
    fuel_header = EcalcYamlKeywords.consumer_tabular_fuel

    resource_headers = resource.get_headers()

    has_fuel = fuel_header in resource_headers

    energy_usage_header = fuel_header if has_fuel else power_header

    rate_values = _get_column_or_none(resource, rate_header)
    suction_pressure_values = _get_column_or_none(resource, suction_pressure_header)
    discharge_pressure_values = _get_column_or_none(resource, discharge_pressure_header)
    energy_usage_values = resource.get_column(energy_usage_header)

    # In case of a fuel-driven compressor, the user may provide power interpolation data to emulate turbine power usage in results
    power_interpolation_values = None
    if has_fuel:
        power_interpolation_values = _get_column_or_none(resource, power_header)

    return CompressorTrainSampledDTO(
        energy_usage_values=energy_usage_values,
        energy_usage_type=EnergyUsageType.FUEL if energy_usage_header == fuel_header else EnergyUsageType.POWER,
        rate_values=rate_values,
        suction_pressure_values=suction_pressure_values,
        discharge_pressure_values=discharge_pressure_values,
        energy_usage_adjustment_constant=_get_adjustment_constant(data=facility_data),
        energy_usage_adjustment_factor=_get_adjustment_factor(data=facility_data),
        power_interpolation_values=power_interpolation_values,
    )


def _create_pump_model_single_speed_dto_model_data(
    resource: Resource, facility_data: YamlPumpChartSingleSpeed, **kwargs
) -> PumpModelDTO:
    chart_data = get_single_speed_chart_data(resource=resource)

    chart = SingleSpeedChartDTO(
        speed_rpm=chart_data.speed,
        efficiency_fraction=convert_efficiency_to_fraction(
            efficiency_values=chart_data.efficiency,
            input_unit=YAML_UNIT_MAPPING[facility_data.units.efficiency],
        ),
        rate_actual_m3_hour=convert_rate_to_am3_per_hour(
            rate_values=chart_data.rate, input_unit=YAML_UNIT_MAPPING[facility_data.units.rate]
        ),
        polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
            head_values=chart_data.head, input_unit=YAML_UNIT_MAPPING[facility_data.units.head]
        ),
    )

    head_margin = facility_data.head_margin

    return PumpModelDTO(
        chart=chart,
        energy_usage_adjustment_constant=_get_adjustment_constant(facility_data),
        energy_usage_adjustment_factor=_get_adjustment_factor(facility_data),
        head_margin=head_margin,
    )


def _create_pump_chart_variable_speed_dto_model_data(
    resource: Resource, facility_data: YamlPumpChartVariableSpeed, **kwargs
) -> PumpModelDTO:
    curves_data = chart_curves_as_resource_to_dto_format(resource=resource)

    curves: list[ChartCurveDTO] = [
        ChartCurveDTO(
            speed_rpm=curve["speed"],
            rate_actual_m3_hour=convert_rate_to_am3_per_hour(
                rate_values=curve["rate"],
                input_unit=YAML_UNIT_MAPPING[facility_data.units.rate],
            ),
            polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
                head_values=curve["head"],
                input_unit=YAML_UNIT_MAPPING[facility_data.units.head],
            ),
            efficiency_fraction=convert_efficiency_to_fraction(
                efficiency_values=curve["efficiency"],
                input_unit=YAML_UNIT_MAPPING[facility_data.units.efficiency],
            ),
        )
        for curve in curves_data
    ]

    head_margin = facility_data.head_margin

    return PumpModelDTO(
        chart=VariableSpeedChartDTO(curves=curves),
        energy_usage_adjustment_constant=_get_adjustment_constant(facility_data),
        energy_usage_adjustment_factor=_get_adjustment_factor(facility_data),
        head_margin=head_margin,
    )


def _create_generator_set_dto_model_data(
    resource: Resource, facility_data: YamlGeneratorSetModel, **kwargs
) -> GeneratorSetModel:
    # Extract adjustment constants from facility data
    adjustment_constant = _get_adjustment_constant(facility_data)
    adjustment_factor = _get_adjustment_factor(facility_data)

    # Ensure the 'name' field is present in facility data
    name = getattr(facility_data, "name", "default_generator_set_name")

    # Create and return the GeneratorSetProcessUnit instance
    return GeneratorSetModel(
        name=name,
        resource=resource,
        energy_usage_adjustment_constant=adjustment_constant,
        energy_usage_adjustment_factor=adjustment_factor,
    )


def _default_facility_to_dto_model_data(
    resource: Resource, typ: EnergyModelType, facility_data: YamlFacilityModelBase
) -> EnergyModelUnionType:
    resource_headers = resource.get_headers()
    resource_data = [resource.get_column(header) for header in resource_headers]

    model_data = {
        "typ": typ,
        "headers": resource_headers,
        "data": resource_data,
        "energy_usage_adjustment_constant": _get_adjustment_constant(data=facility_data),
        "energy_usage_adjustment_factor": _get_adjustment_factor(data=facility_data),
    }

    return EnergyModelFactory.create(typ, model_data)


facility_input_to_dto_map = {
    EnergyModelType.COMPRESSOR_SAMPLED: _create_compressor_train_sampled_dto_model_data,
    EnergyModelType.GENERATOR_SET_SAMPLED: _create_generator_set_dto_model_data,
    ChartType.SINGLE_SPEED: _create_pump_model_single_speed_dto_model_data,
    ChartType.VARIABLE_SPEED: _create_pump_chart_variable_speed_dto_model_data,
}


class FacilityInputMapper:
    def __init__(self, resources: Resources):
        self.__resources = resources

    def from_yaml_to_dto(self, data: YamlFacilityModel) -> EnergyModel:
        resource = self.__resources.get(data.file)

        if resource is None:
            raise DataValidationError(
                data.model_dump(),
                f"Unable to find resource '{data.file}'",
                error_key=EcalcYamlKeywords.file,
                dump_flow_style=DumpFlowStyle.BLOCK,
            )

        typ = energy_model_type_map.get(data.type)

        try:
            return facility_input_to_dto_map.get(typ, _default_facility_to_dto_model_data)(
                resource=resource,
                typ=typ,
                facility_data=data,
            )
        except ValidationError as ve:
            raise DtoValidationError(data=data.model_dump(), validation_error=ve) from ve
        except ValidationValueError as vve:
            raise DataValidationError(
                data=data.model_dump(),
                message=str(vve),
                error_key=vve.key,
                dump_flow_style=DumpFlowStyle.BLOCK,
            ) from vve
        except InvalidResourceException as e:
            message = f"Invalid resource '{data.file}'. Reason: {str(e)}"

            raise DataValidationError(
                data=data.model_dump(),
                message=message,
                error_key=EcalcYamlKeywords.file,
                dump_flow_style=DumpFlowStyle.BLOCK,
            ) from e
