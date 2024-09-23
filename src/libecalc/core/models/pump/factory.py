from typing import Any

from libecalc.common.chart_type import ChartType
from libecalc.common.logger import logger
from libecalc.common.serializable_chart import ChartCurveDTO, SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.core.models.chart import SingleSpeedChart, VariableSpeedChart
from libecalc.core.models.pump.pump import PumpModel, PumpSingleSpeed, PumpVariableSpeed
from libecalc.dto import PumpModel as PumpModelDTO


def create_pump_single_speed(pump_model: PumpModelDTO) -> PumpSingleSpeed:
    return PumpSingleSpeed(
        pump_chart=SingleSpeedChart(
            SingleSpeedChartDTO(
                speed_rpm=pump_model.chart.speed_rpm,
                rate_actual_m3_hour=pump_model.chart.rate_actual_m3_hour,
                polytropic_head_joule_per_kg=pump_model.chart.polytropic_head_joule_per_kg,
                efficiency_fraction=pump_model.chart.efficiency_fraction,
            )
        ),
        energy_usage_adjustment_constant=pump_model.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=pump_model.energy_usage_adjustment_factor,
        head_margin=pump_model.head_margin,
    )


def create_pump_variable_speed(pump_model: PumpModelDTO) -> PumpVariableSpeed:
    return PumpVariableSpeed(
        VariableSpeedChart(
            VariableSpeedChartDTO(
                curves=[
                    ChartCurveDTO(
                        speed_rpm=curve.speed_rpm,
                        rate_actual_m3_hour=curve.rate_actual_m3_hour,
                        polytropic_head_joule_per_kg=curve.polytropic_head_joule_per_kg,
                        efficiency_fraction=curve.efficiency_fraction,
                    )
                    for curve in pump_model.chart.curves
                ]
            )
        ),
        energy_usage_adjustment_constant=pump_model.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=pump_model.energy_usage_adjustment_factor,
        head_margin=pump_model.head_margin,
    )


def _invalid_pump_model_type(pump_model_dto: Any):
    try:
        msg = f"Unsupported energy model type: {pump_model_dto.typ}."
        logger.error(msg)
        raise TypeError(msg)
    except AttributeError as e:
        msg = "Unsupported energy model type."
        logger.exception(msg)
        raise TypeError(msg) from e


pump_model_map = {
    ChartType.SINGLE_SPEED: create_pump_single_speed,
    ChartType.VARIABLE_SPEED: create_pump_variable_speed,
}


def create_pump_model(pump_model_dto: PumpModelDTO) -> PumpModel:
    return pump_model_map.get(pump_model_dto.chart.typ, _invalid_pump_model_type)(pump_model_dto)
