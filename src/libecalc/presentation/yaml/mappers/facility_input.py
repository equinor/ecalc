from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlGeneratorSetModel,
    YamlPumpChartSingleSpeed,
    YamlPumpChartVariableSpeed,
)


def _get_float_column_or_none(resource: Resource, header: str) -> list[float] | None:
    try:
        return resource.get_float_column(header)
    except InvalidResourceException:
        return None


def _create_pump_model_single_speed_dto_model_data(
    resource: Resource,
    facility_data: YamlPumpChartSingleSpeed,
) -> PumpModel:
    pump_chart = UserDefinedChartData.from_resource(resource, units=facility_data.units, is_single_speed=True)
    return PumpModel(
        pump_chart=pump_chart,
        head_margin=facility_data.head_margin,
    )


def _create_pump_chart_variable_speed_dto_model_data(
    resource: Resource,
    facility_data: YamlPumpChartVariableSpeed,
) -> PumpModel:
    pump_chart = UserDefinedChartData.from_resource(resource, units=facility_data.units, is_single_speed=False)
    return PumpModel(
        pump_chart=pump_chart,
        head_margin=facility_data.head_margin,
    )


def _create_generator_set_model(
    resource: Resource,
    facility_data: YamlGeneratorSetModel,
) -> GeneratorSetModel:
    # Extract adjustment constants from facility data

    # Create and return the GeneratorSetProcessUnit instance
    return GeneratorSetModel(
        name=facility_data.name,
        resource=resource,
    )
