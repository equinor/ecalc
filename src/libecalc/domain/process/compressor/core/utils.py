from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.domain.process.chart.compressor import (
    SingleSpeedCompressorChart,
    VariableSpeedCompressorChart,
)
from libecalc.domain.process.chart.compressor.chart_creator import (
    CompressorChartCreator,
)
from libecalc.domain.process.chart.compressor.compressor_chart_dto import CompressorChart
from libecalc.domain.process.chart.generic import (
    GenericChartFromDesignPoint,
    GenericChartFromInput,
)
from libecalc.domain.process.chart.generic import GenericChartFromInput as GenericChartFromInputDTO
from libecalc.domain.process.compressor.core.train.stage import (
    CompressorTrainStage,
    UndefinedCompressorStage,
)
from libecalc.domain.process.compressor.dto import CompressorStage


def _create_compressor_chart(
    chart_dto: CompressorChart,
) -> SingleSpeedCompressorChart | VariableSpeedCompressorChart | None:
    if isinstance(chart_dto, SingleSpeedChartDTO):
        return SingleSpeedCompressorChart(chart_dto)
    elif isinstance(chart_dto, VariableSpeedChartDTO):
        return VariableSpeedCompressorChart(chart_dto)
    elif isinstance(chart_dto, GenericChartFromDesignPoint):
        return CompressorChartCreator.from_rate_and_head_design_point(
            design_actual_rate_m3_per_hour=chart_dto.design_rate_actual_m3_per_hour,
            design_head_joule_per_kg=chart_dto.design_polytropic_head_J_per_kg,
            polytropic_efficiency=chart_dto.polytropic_efficiency_fraction,
        )
    elif isinstance(chart_dto, GenericChartFromInput):
        return None
    else:
        raise NotImplementedError(f"Compressor chart type: {chart_dto.typ} has not been implemented.")


def _create_undefined_compressor_train_stage(
    stage_data: CompressorStage,
) -> UndefinedCompressorStage:
    """When we use generic chart from input, we actually mean that we do not define a compressor chart.
        -> The compressor is undefined, and we will create a synthetic one at runtime during actual evaluation.

    Returns a Undefined Compressor Stage with no chart.
    """
    if isinstance(stage_data.compressor_chart, GenericChartFromInputDTO):
        polytropic_efficiency = stage_data.compressor_chart.polytropic_efficiency_fraction
    else:
        raise ValueError("Only GenericChartFromInput is supported for undefined compressor stages.")
    return UndefinedCompressorStage(
        inlet_temperature_kelvin=stage_data.inlet_temperature_kelvin,
        pressure_drop_ahead_of_stage=stage_data.pressure_drop_before_stage,
        remove_liquid_after_cooling=stage_data.remove_liquid_after_cooling,
        polytropic_efficiency=polytropic_efficiency,
    )


def _create_compressor_train_stage(
    stage_data: CompressorStage,
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


def map_compressor_train_stage_to_domain(stage_dto: CompressorStage) -> CompressorTrainStage:
    """Todo: Add multiple streams and pressures here."""
    if isinstance(stage_dto, CompressorStage):
        if isinstance(
            stage_dto.compressor_chart, VariableSpeedChartDTO | GenericChartFromDesignPoint | SingleSpeedChartDTO
        ):
            return _create_compressor_train_stage(stage_dto)
        elif isinstance(stage_dto.compressor_chart, GenericChartFromInput):
            return _create_undefined_compressor_train_stage(stage_dto)
    raise ValueError(f"Compressor stage typ {stage_dto.type_} has not been implemented.")
