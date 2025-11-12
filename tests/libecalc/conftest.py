import pandas as pd
import pytest

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.direct_consumer_function import (
    DirectConsumerFunction,
)
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.dto import InterstagePressureControl
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import Chart, ChartData
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.regularity import Regularity
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.expression_time_series_power import ExpressionTimeSeriesPower
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.testing.chart_data_factory import ChartDataFactory


@pytest.fixture
def regularity_factory():
    def create_regularity(expression_evaluator: ExpressionEvaluator, regularity_value: ExpressionType = 1):
        regularity = Regularity(
            expression_input=regularity_value,
            expression_evaluator=expression_evaluator,
            target_period=expression_evaluator.get_period(),
        )
        return regularity

    return create_regularity


@pytest.fixture
def direct_expression_model_factory(regularity_factory):
    def create_direct_expression_model(
        expression: ExpressionType,
        energy_usage_type: EnergyUsageType,
        expression_evaluator: ExpressionEvaluator,
        consumption_rate_type: RateType = RateType.STREAM_DAY,
        regularity: Regularity | None = None,
    ):
        if regularity is None:
            regularity = regularity_factory(expression_evaluator)

        usage_expression = TimeSeriesExpression(expression=expression, expression_evaluator=expression_evaluator)
        usage_power = ExpressionTimeSeriesPower(
            time_series_expression=usage_expression, regularity=regularity, consumption_rate_type=consumption_rate_type
        )
        usage_fuel = ExpressionTimeSeriesFlowRate(
            time_series_expression=usage_expression, regularity=regularity, consumption_rate_type=consumption_rate_type
        )

        if energy_usage_type == EnergyUsageType.POWER:
            return DirectConsumerFunction(
                energy_usage_type=energy_usage_type,
                load=usage_power,
                power_loss_factor=None,
            )
        else:
            return DirectConsumerFunction(
                energy_usage_type=energy_usage_type,
                fuel_rate=usage_fuel,
                power_loss_factor=None,
            )

    return create_direct_expression_model


@pytest.fixture
def chart_curve_factory():
    def create_chart_curve(
        rate_actual_m3_hour: list[float] = None,
        polytropic_head_joule_per_kg: list[float] = None,
        efficiency_fraction: list[float] = None,
        speed_rpm: float = None,
    ):
        return ChartCurve(
            speed_rpm=speed_rpm,
            rate_actual_m3_hour=rate_actual_m3_hour,
            polytropic_head_joule_per_kg=polytropic_head_joule_per_kg,
            efficiency_fraction=efficiency_fraction,
        )

    return create_chart_curve


@pytest.fixture
def chart_data_factory():
    return ChartDataFactory()


@pytest.fixture
def compressor_chart_factory(chart_data_factory):
    def create_compressor_chart(chart_data: ChartData) -> Chart:
        return CompressorChart(chart_data)

    return create_compressor_chart


@pytest.fixture
def pump_chart_factory(chart_data_factory):
    def create_pump_chart(chart_data: ChartData) -> Chart:
        return Chart(chart_data)

    return create_pump_chart


@pytest.fixture
def variable_speed_compressor_chart_data(chart_data_factory, chart_curve_factory) -> ChartData:
    df = pd.DataFrame(
        [
            [10767, 4053.0, 161345.0, 0.72],
            [10767, 4501.0, 157754.0, 0.73],
            [10767, 4999.0, 152506.0, 0.74],
            [10767, 5493.0, 143618.0, 0.74],
            [10767, 6001.0, 131983.0, 0.72],
            [10767, 6439.0, 117455.0, 0.70],
            [11533, 4328.0, 185232.0, 0.72],
            [11533, 4999.0, 178885.0, 0.74],
            [11533, 5506.0, 171988.0, 0.74],
            [11533, 6028.0, 161766.0, 0.74],
            [11533, 6507.0, 147512.0, 0.72],
            [11533, 6908.0, 133602.0, 0.70],
            [10984, 4139.0, 167544.0, 0.72],
            [10984, 5002.0, 159657.0, 0.74],
            [10984, 5494.0, 151358.0, 0.74],
            [10984, 6009.0, 139910.0, 0.73],
            [10984, 6560.0, 121477.0, 0.70],
            [10435, 3928.0, 151417.0, 0.72],
            [10435, 4507.0, 146983.0, 0.74],
            [10435, 5002.0, 140773.0, 0.74],
            [10435, 5499.0, 131071.0, 0.74],
            [10435, 6249.0, 109705.0, 0.70],
            [9886, 3709.0, 135819.0, 0.72],
            [9886, 4502.0, 129325.0, 0.74],
            [9886, 4994.0, 121889.0, 0.74],
            [9886, 5508.0, 110617.0, 0.73],
            [9886, 5924.0, 98629.70, 0.70],
            [8787, 3306.0, 107429.0, 0.72],
            [8787, 4000.0, 101955.0, 0.74],
            [8787, 4499.0, 95225.60, 0.74],
            [8787, 4997.0, 84307.10, 0.72],
            [8787, 5242.0, 78234.70, 0.70],
            [7689, 2900.0, 82531.50, 0.72],
            [7689, 3504.0, 78440.70, 0.74],
            [7689, 4003.0, 72240.80, 0.74],
            [7689, 4595.0, 60105.80, 0.70],
        ],
        columns=["speed", "rate", "head", "efficiency"],
    )
    chart_curves = [
        chart_curve_factory(
            polytropic_head_joule_per_kg=data["head"].tolist(),
            rate_actual_m3_hour=data["rate"].tolist(),
            efficiency_fraction=data["efficiency"].tolist(),
            speed_rpm=float(speed),
        )
        for speed, data in df.groupby("speed")
    ]

    return chart_data_factory.from_curves(curves=chart_curves)


@pytest.fixture
def compressor_stage_factory():
    def create_compressor_stage(
        compressor_chart_data: ChartData,
        inlet_temperature_kelvin: float = 303.15,
        remove_liquid_after_cooling: bool = False,
        pressure_drop_ahead_of_stage: float = 0.0,
        interstage_pressure_control: InterstagePressureControl | None = None,
    ):
        return CompressorTrainStage(
            compressor_chart=CompressorChart(chart_data=compressor_chart_data),
            inlet_temperature_kelvin=inlet_temperature_kelvin,
            remove_liquid_after_cooling=remove_liquid_after_cooling,
            pressure_drop_ahead_of_stage=pressure_drop_ahead_of_stage,
            interstage_pressure_control=interstage_pressure_control,
        )

    return create_compressor_stage


@pytest.fixture
def compressor_stages(variable_speed_compressor_chart_data, compressor_stage_factory):
    def create_stages(
        nr_stages: int = 1,
        chart_data: ChartData = variable_speed_compressor_chart_data,
        inlet_temperature_kelvin: float = 303.15,
        remove_liquid_after_cooling: bool = False,
        pressure_drop_before_stage: float = 0.0,
        interstage_pressure_control: InterstagePressureControl = None,
    ) -> list[CompressorTrainStage]:
        return [
            compressor_stage_factory(
                compressor_chart_data=chart_data,
                inlet_temperature_kelvin=inlet_temperature_kelvin,
                remove_liquid_after_cooling=remove_liquid_after_cooling,
                pressure_drop_ahead_of_stage=pressure_drop_before_stage,
                interstage_pressure_control=interstage_pressure_control,
            )
        ] * nr_stages

    return create_stages


@pytest.fixture
def variable_speed_compressor_train(
    fluid_model_medium,
    process_simulator_variable_compressor_chart,
    compressor_stages,
):
    def create_compressor_train(
        energy_adjustment_constant: float = 0,
        energy_adjustment_factor: float = 1,
        stages: list[CompressorTrainStage] = None,
        pressure_control: FixedSpeedPressureControl = FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
        nr_stages: int = 1,
        chart_data: ChartData | None = None,
    ) -> CompressorTrainCommonShaft:
        if chart_data is None:
            chart_data = process_simulator_variable_compressor_chart
        if stages is None:
            stages = compressor_stages(chart_data=chart_data) * nr_stages

        return CompressorTrainCommonShaft(
            stages=stages,
            shaft=VariableSpeedShaft(),
            energy_usage_adjustment_constant=energy_adjustment_constant,
            energy_usage_adjustment_factor=energy_adjustment_factor,
            pressure_control=pressure_control,
            calculate_max_rate=calculate_max_rate,
            maximum_power=maximum_power,
        )

    return create_compressor_train


@pytest.fixture()
def process_simulator_variable_compressor_chart(chart_curve_factory, chart_data_factory) -> ChartData:
    chart_curves = [
        chart_curve_factory(
            polytropic_head_joule_per_kg=[82531.50, 78440.70, 72240.80, 60105.80],
            rate_actual_m3_hour=[2900, 3504, 4003, 4595],
            efficiency_fraction=[0.72, 0.74, 0.74, 0.70],
            speed_rpm=7689,
        ),
        chart_curve_factory(
            polytropic_head_joule_per_kg=[135819, 129325, 121889, 110617, 98629.7],
            rate_actual_m3_hour=[3709, 4502, 4994, 5508, 5924],
            efficiency_fraction=[0.72, 0.74, 0.74, 0.73, 0.70],
            speed_rpm=9886,
        ),
        chart_curve_factory(
            polytropic_head_joule_per_kg=[185232, 178885, 171988, 161766, 147512, 133602],
            rate_actual_m3_hour=[4328, 4999, 5506, 6028, 6507, 6908],
            efficiency_fraction=[0.72, 0.74, 0.74, 0.74, 0.72, 0.70],
            speed_rpm=11533,
        ),
    ]
    return chart_data_factory.from_curves(curves=chart_curves)
