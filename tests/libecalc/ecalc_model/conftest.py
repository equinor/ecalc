from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.common.utils.rates import RateType
from libecalc.ecalc_model.equipment.pump_equipment import PumpEquipment
from libecalc.ecalc_model.process.liquid_recirculation_loop import LiquidRecirculationLoop
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesInletProcessUnit,
    TimeSeriesOutletProcessUnit,
    TimeSeriesProcessUnit,
    TimeSeriesPumpProcessUnit,
)
from libecalc.ecalc_model.process.pump_pipeline import PumpPipeline
from libecalc.ecalc_model.pump_simulation import PumpConstraint, PumpProblem
from libecalc.ecalc_model.time_series_liquid_stream import TimeSeriesLiquidStream
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.process.chart.chart import ChartCurve, ChartData

PERIODS = [
    Period(datetime(2025, 1, 1), datetime(2026, 1, 1)),
    Period(datetime(2026, 1, 1), datetime(2027, 1, 1)),
]


@pytest.fixture
def periods() -> list[Period]:
    return list(PERIODS)


@pytest.fixture
def pump_chart(chart_data_factory) -> ChartData:
    return chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=1,
                rate_actual_m3_hour=[277.0, 524.0, 666.0, 832.0, 927.0],
                polytropic_head_joule_per_kg=[10415.277, 9845.316, 9254.754, 8308.089, 7605.693],
                efficiency_fraction=[0.4759, 0.6426, 0.6871, 0.7052, 0.6908],
            )
        ]
    )


@pytest.fixture
def pump_equipment() -> PumpEquipment:
    return PumpEquipment(name="pump")


@pytest.fixture
def pump_unit_factory(pump_chart, pump_equipment):
    def create(minimum_flow_rate_m3_per_hour: float | None = None) -> TimeSeriesPumpProcessUnit:
        return TimeSeriesPumpProcessUnit(
            pump_chart=pump_chart,
            pump_equipment_id=pump_equipment.get_id(),
            minimum_flow_rate_m3_per_hour=minimum_flow_rate_m3_per_hour,
        )

    return create


@pytest.fixture
def process_units_factory(pump_unit_factory):
    def create(pump: TimeSeriesPumpProcessUnit | None = None) -> list[TimeSeriesProcessUnit]:
        return [
            TimeSeriesInletProcessUnit(),
            TimeSeriesDirectMixerProcessUnit(),
            pump or pump_unit_factory(),
            TimeSeriesDirectSplitterProcessUnit(),
            TimeSeriesChokeProcessUnit(),
            TimeSeriesOutletProcessUnit(),
        ]

    return create


@pytest.fixture
def pump_pipeline_factory(process_units_factory):
    def create(name: str = "water_injection") -> PumpPipeline:
        process_units = process_units_factory()
        _inlet, mixer, _pump, splitter, _choke, _outlet = process_units
        return PumpPipeline(
            name=name,
            process_units=process_units,
            process_periods=PERIODS,
            recirculation_loops=[
                LiquidRecirculationLoop(
                    mixer_process_unit_id=mixer.get_id(), splitter_process_unit_id=splitter.get_id()
                )
            ],
        )

    return create


@pytest.fixture
def expression_evaluator(expression_evaluator_factory):
    return expression_evaluator_factory.from_periods(
        periods=PERIODS,
        variables={"$var.outlet_pressure": [150.0, 200.0]},
    )


@pytest.fixture
def expression_factory(expression_evaluator):
    def create(expression: ExpressionType) -> TimeSeriesExpression:
        return TimeSeriesExpression(expression=expression, expression_evaluator=expression_evaluator)

    return create


@pytest.fixture
def liquid_stream_factory(expression_evaluator, expression_factory, make_time_series_flow_rate, regularity_factory):
    def create(
        rate: ExpressionType = 12000, pressure: ExpressionType = 10, density: ExpressionType = 1010
    ) -> TimeSeriesLiquidStream:
        return TimeSeriesLiquidStream(
            volumetric_rate_m3_per_day=make_time_series_flow_rate(
                value=rate,
                evaluator=expression_evaluator,
                regularity=regularity_factory(expression_evaluator),
                rate_type=RateType.STREAM_DAY,
            ),
            pressure_bara=expression_factory(pressure),
            density_kg_per_m3=expression_factory(density),
        )

    return create


@pytest.fixture
def pump_problem_factory(expression_factory):
    def create(pump_pipeline: PumpPipeline, outlet_pressure: ExpressionType = "$var.outlet_pressure") -> PumpProblem:
        choke = pump_pipeline.get_process_units()[-2]
        outlet_connection = pump_pipeline.get_process_unit_connections()[-1]
        return PumpProblem(
            constraint=PumpConstraint(
                outlet_pressure=expression_factory(outlet_pressure),
                target_process_unit_id=choke.get_id(),
                target_process_connection_id=outlet_connection.get_id(),
            ),
            pump_pipeline_id=pump_pipeline.get_id(),
        )

    return create
