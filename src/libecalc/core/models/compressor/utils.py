from typing import Optional, Union

from libecalc import dto
from libecalc.core.models.compressor.train.chart import (
    SingleSpeedCompressorChart,
    VariableSpeedCompressorChart,
)
from libecalc.core.models.compressor.train.chart.chart_creator import (
    CompressorChartCreator,
)
from libecalc.core.models.compressor.train.stage import (
    CompressorTrainStage,
    UndefinedCompressorStage,
)


def _create_compressor_chart(
    chart_dto: dto.CompressorChart,
) -> Optional[Union[SingleSpeedCompressorChart, VariableSpeedCompressorChart]]:
    if isinstance(chart_dto, dto.SingleSpeedChart):
        return SingleSpeedCompressorChart(chart_dto)
    elif isinstance(chart_dto, dto.VariableSpeedChart):
        return VariableSpeedCompressorChart(chart_dto)
    elif isinstance(chart_dto, dto.GenericChartFromDesignPoint):
        return CompressorChartCreator.from_rate_and_head_design_point(
            design_actual_rate_m3_per_hour=chart_dto.design_rate_actual_m3_per_hour,
            design_head_joule_per_kg=chart_dto.design_polytropic_head_J_per_kg,
            polytropic_efficiency=chart_dto.polytropic_efficiency_fraction,
        )
    elif isinstance(chart_dto, dto.GenericChartFromInput):
        return None
    else:
        raise NotImplementedError(f"Compressor chart type: {chart_dto.typ} has not been implemented.")


def _create_undefined_compressor_train_stage(
    stage_data: dto.CompressorStage,
) -> UndefinedCompressorStage:
    """When we use generic chart from input, we actually mean that we do not define a compressor chart.
        -> The compressor is undefined, and we will create a synthetic one at runtime during actual evaluation.

    Returns a Undefined Compressor Stage with no chart.
    """
    if isinstance(stage_data.compressor_chart, dto.GenericChartFromInput):
        polytropic_efficiency = stage_data.compressor_chart.polytropic_efficiency_fraction
    else:
        raise ValueError("Only GenericChartFromInput is supported for undefined compressor stages.")
    return UndefinedCompressorStage(
        inlet_temperature_kelvin=stage_data.inlet_temperature_kelvin,
        pressure_drop_ahead_of_stage=stage_data.pressure_drop_before_stage,
        remove_liquid_after_cooling=stage_data.remove_liquid_after_cooling,
        polytropic_efficiency=polytropic_efficiency,
    )


def _create_single_speed_compressor_train_stage(
    stage_data: dto.CompressorStage,
) -> CompressorTrainStage:
    compressor_chart = _create_compressor_chart(stage_data.compressor_chart)
    return CompressorTrainStage(
        compressor_chart=compressor_chart,
        inlet_temperature_kelvin=stage_data.inlet_temperature_kelvin,
        pressure_drop_ahead_of_stage=stage_data.pressure_drop_before_stage,
        remove_liquid_after_cooling=stage_data.remove_liquid_after_cooling,
    )


def _create_variable_speed_compressor_train_stage(
    stage_data: dto.CompressorStage,
) -> CompressorTrainStage:
    compressor_chart = _create_compressor_chart(stage_data.compressor_chart)
    if stage_data.control_margin > 0:
        compressor_chart = compressor_chart.get_chart_adjusted_for_control_margin(
            control_margin=stage_data.control_margin
        )
    return CompressorTrainStage(
        inlet_temperature_kelvin=stage_data.inlet_temperature_kelvin,
        compressor_chart=compressor_chart,
        pressure_drop_ahead_of_stage=stage_data.pressure_drop_before_stage,
        remove_liquid_after_cooling=stage_data.remove_liquid_after_cooling,
    )


def map_compressor_train_stage_to_domain(stage_dto: dto.CompressorStage) -> CompressorTrainStage:
    """Todo: Add multiple streams and pressures here."""
    if isinstance(stage_dto, dto.CompressorStage):
        if isinstance(stage_dto.compressor_chart, (dto.VariableSpeedChart, dto.GenericChartFromDesignPoint)):
            return _create_variable_speed_compressor_train_stage(stage_dto)
        elif isinstance(stage_dto.compressor_chart, dto.SingleSpeedChart):
            return _create_single_speed_compressor_train_stage(stage_dto)
        elif isinstance(stage_dto.compressor_chart, dto.GenericChartFromInput):
            return _create_undefined_compressor_train_stage(stage_dto)
    raise ValueError(f"Compressor stage typ {stage_dto.type_} has not been implemented.")
