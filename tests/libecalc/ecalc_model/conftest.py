from collections.abc import Sequence
from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.common.utils.rates import RateType
from libecalc.ecalc_model.equipment.equipment_id import EquipmentId
from libecalc.ecalc_model.equipment.pump_equipment import PumpEquipment
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesInletProcessUnit,
    TimeSeriesOutletProcessUnit,
    TimeSeriesProcessUnit,
    TimeSeriesPumpProcessUnit,
)
from libecalc.ecalc_model.process.pump.liquid_recirculation_loop import LiquidRecirculationLoop
from libecalc.ecalc_model.process.pump.pump_pipeline import PumpPipeline
from libecalc.ecalc_model.process.pump.pump_simulation import PumpConstraint, PumpProblem, PumpProblemId
from libecalc.ecalc_model.process.pump.time_series_liquid_stream import TimeSeriesLiquidStream
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.process.chart.chart import ChartData
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId, ProcessUnitConnectionId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.testing.pump_test_data import single_speed_pump_chart

PERIODS = [
    Period(datetime(2025, 1, 1), datetime(2026, 1, 1)),
    Period(datetime(2026, 1, 1), datetime(2027, 1, 1)),
]


@pytest.fixture
def periods() -> list[Period]:
    return list(PERIODS)


@pytest.fixture
def pump_chart() -> ChartData:
    return single_speed_pump_chart()


@pytest.fixture
def pump_equipment() -> PumpEquipment:
    return PumpEquipment(name="pump")


@pytest.fixture
def pump_unit_factory(pump_chart):
    def create(
        pump_chart: ChartData = pump_chart,
        pump_equipment_id: EquipmentId | None = None,
        minimum_flow_rate_m3_per_hour: float | None = None,
        process_unit_id: ProcessUnitId | None = None,
    ) -> TimeSeriesPumpProcessUnit:
        return TimeSeriesPumpProcessUnit(
            pump_chart=pump_chart,
            pump_equipment_id=pump_equipment_id or PumpEquipment(name="pump").get_id(),
            minimum_flow_rate_m3_per_hour=minimum_flow_rate_m3_per_hour,
            process_unit_id=process_unit_id,
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
    def create(
        name: str = "water_injection",
        process_units: Sequence[TimeSeriesProcessUnit] | None = None,
        process_periods: list[Period] | None = None,
        recirculation_loops: Sequence[LiquidRecirculationLoop] | None = None,
        process_pipeline_id: ProcessPipelineId | None = None,
    ) -> PumpPipeline:
        if process_units is None:
            process_units = process_units_factory()
            if recirculation_loops is None:
                _inlet, mixer, _pump, splitter, _choke, _outlet = process_units
                recirculation_loops = [
                    LiquidRecirculationLoop(
                        mixer_process_unit_id=mixer.get_id(), splitter_process_unit_id=splitter.get_id()
                    )
                ]
        return PumpPipeline(
            name=name,
            process_units=process_units,
            process_periods=process_periods if process_periods is not None else list(PERIODS),
            recirculation_loops=recirculation_loops,
            process_pipeline_id=process_pipeline_id,
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
    def create(
        pump_pipeline: PumpPipeline,
        outlet_pressure: ExpressionType = "$var.outlet_pressure",
        target_process_unit_id: ProcessUnitId | None = None,
        target_process_connection_id: ProcessUnitConnectionId | None = None,
        choke_pressure_control_id: ProcessUnitId | None = None,
        pump_problem_id: PumpProblemId | None = None,
    ) -> PumpProblem:
        return PumpProblem(
            constraint=PumpConstraint(
                outlet_pressure=expression_factory(outlet_pressure),
                target_process_unit_id=target_process_unit_id or pump_pipeline.get_process_units()[-2].get_id(),
                target_process_connection_id=target_process_connection_id
                or pump_pipeline.get_process_unit_connections()[-1].get_id(),
            ),
            pump_pipeline_id=pump_pipeline.get_id(),
            choke_pressure_control_id=choke_pressure_control_id,
            pump_problem_id=pump_problem_id,
        )

    return create
