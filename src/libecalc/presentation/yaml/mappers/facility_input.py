from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.common.serializable_chart import ChartCurveDTO, ChartDTO
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.value_objects.chart import Chart
from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.mappers.utils import (
    YAML_UNIT_MAPPING,
    chart_curves_as_resource_to_dto_format,
    convert_efficiency_to_fraction,
    convert_head_to_joule_per_kg,
    convert_rate_to_am3_per_hour,
    get_single_speed_chart_data,
)
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
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


def _get_float_column_or_none(resource: Resource, header: str) -> list[float] | None:
    try:
        return resource.get_float_column(header)
    except InvalidResourceException:
        return None


def _create_pump_model_single_speed_dto_model_data(
    resource: Resource,
    facility_data: YamlPumpChartSingleSpeed,
) -> PumpModel:
    chart_data = get_single_speed_chart_data(resource=resource)
    pump_chart = Chart(
        ChartDTO(
            curves=[
                ChartCurveDTO(
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
            ]
        )
    )
    return PumpModel(
        pump_chart=pump_chart,
        energy_usage_adjustment_constant=_get_adjustment_constant(facility_data),
        energy_usage_adjustment_factor=_get_adjustment_factor(facility_data),
        head_margin=facility_data.head_margin,
    )


def _create_pump_chart_variable_speed_dto_model_data(
    resource: Resource,
    facility_data: YamlPumpChartVariableSpeed,
) -> PumpModel:
    curves_data = chart_curves_as_resource_to_dto_format(resource=resource)
    pump_chart = Chart(
        ChartDTO(
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
    return PumpModel(
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
