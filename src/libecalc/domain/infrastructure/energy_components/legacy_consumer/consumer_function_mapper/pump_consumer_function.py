from libecalc.common.chart_type import ChartType
from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.domain.infrastructure.energy_components.pump.pump_energy_component import PumpEnergyComponent
from libecalc.domain.process.core.chart import SingleSpeedChart, VariableSpeedChart
from libecalc.domain.process.pump.pump_process_unit import PumpProcessUnit, PumpSingleSpeed, PumpVariableSpeed
from libecalc.expression import Expression


def create_pump_consumer_function(
    chart_type: ChartType,
    chart: SingleSpeedChartDTO | VariableSpeedChartDTO,
    energy_usage_adjustment_constant: float,
    energy_usage_adjustment_factor: float,
    head_margin: float,
    rate_standard_m3_day: Expression,
    suction_pressure: Expression,
    discharge_pressure: Expression,
    fluid_density: Expression,
    power_loss_factor: Expression | None = None,
    condition: Expression | None = None,
) -> PumpEnergyComponent:
    if chart_type == ChartType.SINGLE_SPEED:
        pump_process_unit = PumpSingleSpeed(
            pump_chart=SingleSpeedChart(chart),
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            head_margin=head_margin,
        )
    elif chart_type == ChartType.VARIABLE_SPEED:
        pump_process_unit = PumpVariableSpeed(
            pump_chart=VariableSpeedChart(chart),
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            head_margin=head_margin,
        )
    else:
        PumpProcessUnit._invalid_pump_model_type(chart_type)

    return PumpEnergyComponent(
        name="How to send in name here?",
        condition_expression=condition,
        power_loss_factor_expression=power_loss_factor,
        pump_process_unit=pump_process_unit,
        rate_expression=rate_standard_m3_day,
        suction_pressure_expression=suction_pressure,
        discharge_pressure_expression=discharge_pressure,
        fluid_density_expression=fluid_density,
    )
