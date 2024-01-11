from typing import Dict, List, Union

from pydantic import TypeAdapter, ValidationError

from libecalc import dto
from libecalc.dto import CompressorSampled as CompressorTrainSampledDTO
from libecalc.dto import GeneratorSetSampled, TabulatedData
from libecalc.dto.types import ChartType, EnergyModelType, EnergyUsageType
from libecalc.presentation.yaml.mappers.utils import (
    chart_curves_as_resource_to_dto_format,
    convert_efficiency_to_fraction,
    convert_head_to_joule_per_kg,
    convert_rate_to_am3_per_hour,
    get_single_speed_chart_data,
    get_units_from_chart_config,
)
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
    DumpFlowStyle,
    ValidationValueError,
)
from libecalc.presentation.yaml.yaml_entities import Resource, Resources
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords

# Used here to make pydantic understand which object to instantiate.
EnergyModelUnionType = Union[GeneratorSetSampled, TabulatedData, CompressorTrainSampledDTO]

energy_model_type_map = {
    EcalcYamlKeywords.facility_type_electricity2fuel: EnergyModelType.GENERATOR_SET_SAMPLED,
    EcalcYamlKeywords.facility_type_pump_chart_single_speed: ChartType.SINGLE_SPEED,
    EcalcYamlKeywords.facility_type_pump_chart_variable_speed: ChartType.VARIABLE_SPEED,
    EcalcYamlKeywords.facility_type_compressor_tabular: EnergyModelType.COMPRESSOR_SAMPLED,
    EcalcYamlKeywords.facility_type_tabular: EnergyModelType.TABULATED,
}

PUMP_CHART_TYPES = [ChartType.SINGLE_SPEED, ChartType.VARIABLE_SPEED]


def _get_adjustment_constant(data: Dict) -> float:
    return data.get(EcalcYamlKeywords.facility_adjustment, {}).get(EcalcYamlKeywords.facility_adjustment_constant) or 0


def _get_adjustment_factor(data: Dict) -> float:
    return data.get(EcalcYamlKeywords.facility_adjustment, {}).get(EcalcYamlKeywords.facility_adjustment_factor) or 1


def _create_compressor_train_sampled_dto_model_data(
    resource: Resource, facility_data, **kwargs
) -> CompressorTrainSampledDTO:
    # kwargs just to allow this to be used with _default_facility_to_dto_model_data which needs type until we have
    # replaced _default_facility_to_dto_model_data and have separate functions for all types
    rate_header = EcalcYamlKeywords.consumer_function_rate
    suction_pressure_header = EcalcYamlKeywords.consumer_function_suction_pressure
    discharge_pressure_header = EcalcYamlKeywords.consumer_function_discharge_pressure
    power_header = EcalcYamlKeywords.consumer_tabular_power
    fuel_header = EcalcYamlKeywords.consumer_tabular_fuel

    energy_usage_header = fuel_header if fuel_header in resource.headers else power_header
    energy_usage_index = resource.headers.index(energy_usage_header)
    rate_index = resource.headers.index(rate_header) if rate_header in resource.headers else None
    suction_pressure_index = (
        resource.headers.index(suction_pressure_header) if suction_pressure_header in resource.headers else None
    )
    discharge_pressure_index = (
        resource.headers.index(discharge_pressure_header) if discharge_pressure_header in resource.headers else None
    )

    columns = resource.data
    rate_values = list(columns[rate_index]) if rate_index is not None else None
    suction_pressure_values = list(columns[suction_pressure_index]) if suction_pressure_index is not None else None
    discharge_pressure_values = (
        list(columns[discharge_pressure_index]) if discharge_pressure_index is not None else None
    )
    energy_usage_values = list(columns[energy_usage_index])

    # In case of a fuel-driver compressor, the user may provide power interpolation data to emulate turbine power usage in results
    power_interpolation_values = None
    if fuel_header in resource.headers:
        power_interpolation_header = power_header if power_header in resource.headers else None
        if power_interpolation_header:
            power_interpolation_index = resource.headers.index(power_interpolation_header)
            power_interpolation_values = list(columns[power_interpolation_index])

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


def _create_pump_model_single_speed_dto_model_data(resource: Resource, facility_data, **kwargs) -> dto.PumpModel:
    units = get_units_from_chart_config(chart_config=facility_data)
    resource_name = facility_data.get(EcalcYamlKeywords.file)

    chart_data = get_single_speed_chart_data(resource=resource, resource_name=resource_name)

    chart = dto.SingleSpeedChart(
        speed_rpm=chart_data.speed,
        efficiency_fraction=convert_efficiency_to_fraction(
            efficiency_values=chart_data.efficiency,
            input_unit=units[EcalcYamlKeywords.consumer_chart_efficiency],
        ),
        rate_actual_m3_hour=convert_rate_to_am3_per_hour(
            rate_values=chart_data.rate, input_unit=units[EcalcYamlKeywords.consumer_chart_rate]
        ),
        polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
            head_values=chart_data.head, input_unit=units[EcalcYamlKeywords.consumer_chart_head]
        ),
    )

    head_margin = facility_data.get(EcalcYamlKeywords.pump_system_head_margin, 0.0)

    return dto.PumpModel(
        chart=chart,
        energy_usage_adjustment_constant=_get_adjustment_constant(facility_data),
        energy_usage_adjustment_factor=_get_adjustment_factor(facility_data),
        head_margin=head_margin,
    )


def _create_pump_chart_variable_speed_dto_model_data(resource: Resource, facility_data, **kwargs) -> dto.PumpModel:
    units = get_units_from_chart_config(chart_config=facility_data)

    resource_name = facility_data.get(EcalcYamlKeywords.file)
    curves_data = chart_curves_as_resource_to_dto_format(resource=resource, resource_name=resource_name)

    curves: List[dto.ChartCurve] = [
        dto.ChartCurve(
            speed_rpm=curve["speed"],
            rate_actual_m3_hour=convert_rate_to_am3_per_hour(
                rate_values=curve["rate"], input_unit=units[EcalcYamlKeywords.consumer_chart_rate]
            ),
            polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
                head_values=curve["head"], input_unit=units[EcalcYamlKeywords.consumer_chart_head]
            ),
            efficiency_fraction=convert_efficiency_to_fraction(
                efficiency_values=curve["efficiency"],
                input_unit=units[EcalcYamlKeywords.consumer_chart_efficiency],
            ),
        )
        for curve in curves_data
    ]

    head_margin = facility_data.get(EcalcYamlKeywords.pump_system_head_margin, 0.0)

    return dto.PumpModel(
        chart=dto.VariableSpeedChart(curves=curves),
        energy_usage_adjustment_constant=_get_adjustment_constant(facility_data),
        energy_usage_adjustment_factor=_get_adjustment_factor(facility_data),
        head_margin=head_margin,
    )


def _default_facility_to_dto_model_data(
    resource: Resource, typ: EnergyModelType, facility_data: Dict
) -> EnergyModelUnionType:
    model_data = {
        "typ": typ,
        "headers": resource.headers,
        "data": resource.data,
        "energy_usage_adjustment_constant": _get_adjustment_constant(data=facility_data),
        "energy_usage_adjustment_factor": _get_adjustment_factor(data=facility_data),
    }

    return TypeAdapter(EnergyModelUnionType).validate_python(model_data)


facility_input_to_dto_map = {
    EnergyModelType.COMPRESSOR_SAMPLED: _create_compressor_train_sampled_dto_model_data,
    ChartType.SINGLE_SPEED: _create_pump_model_single_speed_dto_model_data,
    ChartType.VARIABLE_SPEED: _create_pump_chart_variable_speed_dto_model_data,
}


class FacilityInputMapper:
    def __init__(self, resources: Resources):
        self.__resources = resources

    def from_yaml_to_dto(self, data: Dict) -> dto.EnergyModel:
        resource = self.__resources.get(data.get(EcalcYamlKeywords.file), Resource(headers=[], data=[]))
        typ = energy_model_type_map.get(data.get(EcalcYamlKeywords.type))

        try:
            return facility_input_to_dto_map.get(typ, _default_facility_to_dto_model_data)(
                resource=resource,
                typ=typ,
                facility_data=data,
            )
        except ValidationError as ve:
            raise DtoValidationError(data=data, validation_error=ve) from ve
        except ValidationValueError as vve:
            raise DataValidationError(
                data=data,
                message=str(vve),
                error_key=vve.key,
                dump_flow_style=DumpFlowStyle.BLOCK,
            ) from vve
