from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.common.serializable_chart import ChartCurveDTO, SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import TabularEnergyFunction
from libecalc.domain.process.compressor.dto import CompressorSampled as CompressorTrainSampledDTO
from libecalc.domain.process.pump.pump import PumpSingleSpeed, PumpVariableSpeed
from libecalc.domain.process.value_objects.chart import SingleSpeedChart, VariableSpeedChart
from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.mappers.utils import (
    YAML_UNIT_MAPPING,
    chart_curves_as_resource_to_dto_format,
    convert_efficiency_to_fraction,
    convert_head_to_joule_per_kg,
    convert_rate_to_am3_per_hour,
    get_single_speed_chart_data,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlCompressorTabularModel,
    YamlFacilityAdjustment,
    YamlFacilityModelBase,
    YamlGeneratorSetModel,
    YamlPumpChartSingleSpeed,
    YamlPumpChartVariableSpeed,
)


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
    resource: Resource,
    facility_data: YamlCompressorTabularModel,
) -> CompressorTrainSampledDTO:
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
        energy_usage_values=energy_usage_values,  # type: ignore[arg-type]
        energy_usage_type=EnergyUsageType.FUEL if energy_usage_header == fuel_header else EnergyUsageType.POWER,
        rate_values=rate_values,  # type: ignore[arg-type]
        suction_pressure_values=suction_pressure_values,  # type: ignore[arg-type]
        discharge_pressure_values=discharge_pressure_values,  # type: ignore[arg-type]
        energy_usage_adjustment_constant=_get_adjustment_constant(data=facility_data),
        energy_usage_adjustment_factor=_get_adjustment_factor(data=facility_data),
        power_interpolation_values=power_interpolation_values,  # type: ignore[arg-type]
    )


def _create_pump_model_single_speed_dto_model_data(
    resource: Resource,
    facility_data: YamlPumpChartSingleSpeed,
) -> PumpSingleSpeed:
    chart_data = get_single_speed_chart_data(resource=resource)
    pump_chart = SingleSpeedChart(
        SingleSpeedChartDTO(
            speed_rpm=chart_data.speed,
            rate_actual_m3_hour=convert_rate_to_am3_per_hour(
                rate_values=chart_data.rate, input_unit=YAML_UNIT_MAPPING[facility_data.units.rate]
            ),
            polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
                head_values=chart_data.head, input_unit=YAML_UNIT_MAPPING[facility_data.units.head]
            ),
            efficiency_fraction=convert_efficiency_to_fraction(
                efficiency_values=chart_data.efficiency,
                input_unit=YAML_UNIT_MAPPING[facility_data.units.efficiency],
            ),
        )
    )
    return PumpSingleSpeed(
        pump_chart=pump_chart,
        energy_usage_adjustment_constant=_get_adjustment_constant(facility_data),
        energy_usage_adjustment_factor=_get_adjustment_factor(facility_data),
        head_margin=facility_data.head_margin,
    )


def _create_pump_chart_variable_speed_dto_model_data(
    resource: Resource,
    facility_data: YamlPumpChartVariableSpeed,
) -> PumpVariableSpeed:
    curves_data = chart_curves_as_resource_to_dto_format(resource=resource)
    pump_chart = VariableSpeedChart(
        VariableSpeedChartDTO(
            curves=[
                ChartCurveDTO(
                    speed_rpm=curve.speed,
                    rate_actual_m3_hour=convert_rate_to_am3_per_hour(
                        rate_values=curve.rate,
                        input_unit=YAML_UNIT_MAPPING[facility_data.units.rate],
                    ),
                    polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
                        head_values=curve.head,
                        input_unit=YAML_UNIT_MAPPING[facility_data.units.head],
                    ),
                    efficiency_fraction=convert_efficiency_to_fraction(
                        efficiency_values=curve.efficiency,
                        input_unit=YAML_UNIT_MAPPING[facility_data.units.efficiency],
                    ),
                )
                for curve in curves_data
            ]
        )
    )
    return PumpVariableSpeed(
        pump_chart=pump_chart,
        energy_usage_adjustment_constant=_get_adjustment_constant(facility_data),
        energy_usage_adjustment_factor=_get_adjustment_factor(facility_data),
        head_margin=facility_data.head_margin,
    )


def _create_generator_set_model(
    resource: Resource,
    facility_data: YamlGeneratorSetModel,
) -> GeneratorSetModel:
    # Extract adjustment constants from facility data
    adjustment_constant = _get_adjustment_constant(facility_data)
    adjustment_factor = _get_adjustment_factor(facility_data)

    # Create and return the GeneratorSetProcessUnit instance
    return GeneratorSetModel(
        name=facility_data.name,
        resource=resource,
        energy_usage_adjustment_constant=adjustment_constant,
        energy_usage_adjustment_factor=adjustment_factor,
    )


def _create_tabulated_model(resource: Resource, facility_data: YamlFacilityModelBase) -> TabularEnergyFunction:
    resource_headers = resource.get_headers()
    resource_data = [resource.get_float_column(header) for header in resource_headers]

    return TabularEnergyFunction(
        headers=resource_headers,
        data=resource_data,
        energy_usage_adjustment_factor=_get_adjustment_factor(data=facility_data),
        energy_usage_adjustment_constant=_get_adjustment_constant(data=facility_data),
    )
