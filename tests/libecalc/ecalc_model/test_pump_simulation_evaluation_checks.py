import re
from collections.abc import Sequence

import pytest

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.units import UnitConstants
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesInletProcessUnit,
    TimeSeriesOutletProcessUnit,
    TimeSeriesPressureDropperProcessUnit,
    TimeSeriesProcessUnit,
)
from libecalc.ecalc_model.process.pump.pump_pipeline import PumpPipeline
from libecalc.ecalc_model.process.pump.pump_simulation import (
    PumpCommonStreamDistributionConfig,
    PumpCommonStreamSettings,
    PumpProblem,
    PumpSimulation,
)
from libecalc.ecalc_model.process.pump.pump_simulation_evaluation import evaluate_pump_simulation
from libecalc.ecalc_model.time_series_configuration import TimeSeriesPressureDropperConfiguration
from libecalc.ecalc_model.validation import InvalidEcalcModelException
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.stream_distribution.common_stream_distribution import Overflow
from libecalc.testing.pump_test_data import DENSITY_KG_PER_M3
from tests.libecalc.ecalc_model.pump_units import PumpUnits, create_pump_problem, create_pump_units

# Every pump has the single-speed chart of the ``pump_chart`` fixture, whose head is 80 bar at 600 m3/h for
# this density, and a choke. The simulation has two periods.
INLET_PRESSURE = 10.0
REQUESTED_OUTLET_PRESSURE = 60.0
RATE_M3_PER_DAY = 600.0 * UnitConstants.HOURS_PER_DAY

type PipelineWithProblems = tuple[PumpPipeline, list[PumpProblem]]
type ProcessConfigurations = dict[ProcessPipelineId, dict[ProcessUnitId, TimeSeriesPressureDropperConfiguration]]


@pytest.fixture
def make_pipeline_with_problems(pump_pipeline_factory, pump_problem_factory):
    """A pump pipeline from an inlet, the given process units and an outlet, and one pump problem per pump."""

    def create(
        name: str, process_units: Sequence[TimeSeriesProcessUnit], pumps: Sequence[PumpUnits]
    ) -> PipelineWithProblems:
        pump_pipeline = pump_pipeline_factory(
            name=name,
            process_units=[TimeSeriesInletProcessUnit(), *process_units, TimeSeriesOutletProcessUnit()],
            recirculation_loops=[pump.recirculation_loop for pump in pumps],
        )
        return pump_pipeline, [
            create_pump_problem(pump_problem_factory, pump_pipeline, pump, outlet_pressure=REQUESTED_OUTLET_PRESSURE)
            for pump in pumps
        ]

    return create


@pytest.fixture
def make_simulation(periods, expression_factory, liquid_stream_factory):
    """A pump simulation whose common stream of 600 m3/h is divided by the given rate fractions in every setting."""

    def create(
        pipelines_with_problems: Sequence[PipelineWithProblems],
        rate_fractions: Sequence[ExpressionType],
        process_configurations: ProcessConfigurations | None = None,
        overflow: Sequence[Overflow] = (),
        number_of_settings: int = 1,
    ) -> PumpSimulation:
        return PumpSimulation(
            name="injection",
            stream_distribution=PumpCommonStreamDistributionConfig(
                inlet_stream=liquid_stream_factory(
                    rate=RATE_M3_PER_DAY, pressure=INLET_PRESSURE, density=DENSITY_KG_PER_M3
                ),
                settings=[
                    PumpCommonStreamSettings(
                        rate_fractions=[expression_factory(rate_fraction) for rate_fraction in rate_fractions],
                        overflow=list(overflow),
                    )
                    for _ in range(number_of_settings)
                ],
            ),
            pump_problems={pump_pipeline.get_id(): problems for pump_pipeline, problems in pipelines_with_problems},
            process_periods=periods,
            process_configurations=process_configurations,
        )

    return create


@pytest.fixture
def make_pressure_drop_configuration(expression_factory):
    def create(pressure_drop_bara: ExpressionType) -> TimeSeriesPressureDropperConfiguration:
        return TimeSeriesPressureDropperConfiguration(pressure_drop_in_bara=expression_factory(pressure_drop_bara))

    return create


def test_result_has_the_ids_of_the_pump_objects_and_the_periods(
    periods, pump_chart, pump_unit_factory, make_pipeline_with_problems, make_simulation
):
    pumps = [create_pump_units(pump_unit_factory(pump_chart=pump_chart), has_choke=True) for _ in range(2)]
    pipelines_with_problems = [
        make_pipeline_with_problems(name, pump.get_process_units(), [pump])
        for name, pump in zip(("A", "B"), pumps, strict=True)
    ]
    simulation = make_simulation(pipelines_with_problems, rate_fractions=[0.5, 0.5])

    # The pump pipelines are given in another order than the simulation lists them.
    result = evaluate_pump_simulation(
        simulation, [pump_pipeline for pump_pipeline, _ in reversed(pipelines_with_problems)]
    )

    assert result.pump_simulation_id == simulation.get_id()
    assert [period_result.period for period_result in result.period_results] == periods
    for period_result in result.period_results:
        for (pump_pipeline, [problem]), pump, pipeline_result in zip(
            pipelines_with_problems, pumps, period_result.pipeline_results, strict=True
        ):
            [problem_result] = pipeline_result.problem_results
            assert pipeline_result.pump_pipeline_id == pump_pipeline.get_id()
            assert list(pipeline_result.connection_streams) == [
                connection.get_id() for connection in pump_pipeline.get_process_unit_connections()
            ]
            assert problem_result.pump_problem_id == problem.get_id()
            assert problem_result.pump_equipment_id == pump.pump.pump_equipment_id
            solution = problem_result.solution
            assert solution.pump_result.process_unit_id == pump.pump.get_id()
            assert [configuration.configuration_handler_id for configuration in solution.configurations] == [
                pump.recirculation_loop.get_id(),
                pump.choke.get_id(),
            ]


def test_rejects_a_pump_pipeline_that_is_not_given(
    pump_chart, pump_unit_factory, make_pipeline_with_problems, make_simulation
):
    pump = create_pump_units(pump_unit_factory(pump_chart=pump_chart), has_choke=True)
    pump_pipeline, problems = make_pipeline_with_problems("A", pump.get_process_units(), [pump])
    simulation = make_simulation([(pump_pipeline, problems)], rate_fractions=[1.0])

    with pytest.raises(
        ProgrammingError,
        match=f"Pump simulation 'injection' refers to pump pipelines that are not given: {pump_pipeline.get_id()}",
    ):
        evaluate_pump_simulation(simulation, [])


def test_rejects_overflow(pump_chart, pump_unit_factory, make_pipeline_with_problems, make_simulation):
    pipelines_with_problems = []
    for name in ("A", "B"):
        pump = create_pump_units(pump_unit_factory(pump_chart=pump_chart), has_choke=True)
        pipelines_with_problems.append(make_pipeline_with_problems(name, pump.get_process_units(), [pump]))
    (pipeline_a, _), (pipeline_b, _) = pipelines_with_problems
    simulation = make_simulation(
        pipelines_with_problems,
        rate_fractions=[1.0, 0.0],
        overflow=[Overflow(from_id=pipeline_a.get_id(), to_id=pipeline_b.get_id())],
    )

    with pytest.raises(ProgrammingError, match="Pump simulation 'injection' has overflow .* which is not supported"):
        evaluate_pump_simulation(simulation, [pipeline_a, pipeline_b])


def test_rejects_the_same_pump_in_two_pipelines(
    pump_chart, pump_unit_factory, make_pipeline_with_problems, make_simulation
):
    first = create_pump_units(pump_unit_factory(pump_chart=pump_chart), has_choke=True)
    second = create_pump_units(
        pump_unit_factory(pump_chart=pump_chart, pump_equipment_id=first.pump.pump_equipment_id), has_choke=True
    )
    pipelines_with_problems = [
        make_pipeline_with_problems(name, pump.get_process_units(), [pump])
        for name, pump in (("A", first), ("B", second))
    ]
    simulation = make_simulation(pipelines_with_problems, rate_fractions=[0.5, 0.5])

    with pytest.raises(
        InvalidEcalcModelException,
        match=f"Pump simulation 'injection' pumps must be unique, got duplicate '{first.pump.pump_equipment_id}'",
    ):
        evaluate_pump_simulation(simulation, [pump_pipeline for pump_pipeline, _ in pipelines_with_problems])


def test_rejects_a_pressure_dropper_with_no_process_configuration(
    pump_chart, pump_unit_factory, make_pipeline_with_problems, make_simulation
):
    pump = create_pump_units(pump_unit_factory(pump_chart=pump_chart), has_choke=True)
    pressure_dropper = TimeSeriesPressureDropperProcessUnit()
    pump_pipeline, problems = make_pipeline_with_problems("A", [pressure_dropper, *pump.get_process_units()], [pump])
    simulation = make_simulation([(pump_pipeline, problems)], rate_fractions=[1.0])

    with pytest.raises(
        ProgrammingError,
        match=f"Pump pipeline 'A' has the pressure dropper '{pressure_dropper.get_id()}', which has no process "
        "configuration in the pump simulation 'injection'",
    ):
        evaluate_pump_simulation(simulation, [pump_pipeline])


def test_rejects_a_process_configuration_for_a_unit_that_is_not_a_pressure_dropper(
    pump_chart, pump_unit_factory, make_pipeline_with_problems, make_simulation, make_pressure_drop_configuration
):
    pump = create_pump_units(pump_unit_factory(pump_chart=pump_chart), has_choke=True)
    pump_pipeline, problems = make_pipeline_with_problems("A", pump.get_process_units(), [pump])
    simulation = make_simulation(
        [(pump_pipeline, problems)],
        rate_fractions=[1.0],
        process_configurations={pump_pipeline.get_id(): {pump.choke.get_id(): make_pressure_drop_configuration(5.0)}},
    )

    with pytest.raises(
        ProgrammingError,
        match=f"Pump pipeline 'A' has a process configuration for '{pump.choke.get_id()}', which is not a pressure "
        "dropper of the pipeline",
    ):
        evaluate_pump_simulation(simulation, [pump_pipeline])


def test_rejects_a_pressure_drop_for_other_periods_than_the_simulation(
    periods, pump_chart, pump_unit_factory, make_pipeline_with_problems, make_simulation, expression_evaluator_factory
):
    pump = create_pump_units(pump_unit_factory(pump_chart=pump_chart), has_choke=True)
    pressure_dropper = TimeSeriesPressureDropperProcessUnit()
    pump_pipeline, problems = make_pipeline_with_problems("A", [pressure_dropper, *pump.get_process_units()], [pump])
    pressure_drop_for_the_first_period = TimeSeriesExpression(
        expression=2.0, expression_evaluator=expression_evaluator_factory.from_periods(periods=periods[:1])
    )
    simulation = make_simulation(
        [(pump_pipeline, problems)],
        rate_fractions=[1.0],
        process_configurations={
            pump_pipeline.get_id(): {
                pressure_dropper.get_id(): TimeSeriesPressureDropperConfiguration(
                    pressure_drop_in_bara=pressure_drop_for_the_first_period
                )
            }
        },
    )

    with pytest.raises(
        InvalidEcalcModelException,
        match="Pump pipeline 'A' pressure drop must be defined for the same periods as the simulation",
    ):
        evaluate_pump_simulation(simulation, [pump_pipeline])


@pytest.mark.parametrize(
    "pressure_dropper_is_after_the_choke, number_of_settings, pressure_drops_bara, message",
    [
        pytest.param(
            False,
            1,
            [2.0, -1.0],
            "Pump pipeline 'A' pressure drop [bara] must not be negative, got -1.0 in {second_period}",
            id="a negative pressure drop",
        ),
        # The pressure drop of 12 bar is above the inlet pressure of 10 bara.
        pytest.param(
            False,
            1,
            [2.0, 12.0],
            "Pump pipeline 'A' gets a pressure that is not positive (-2.0 bara) in {second_period}. "
            "Check its pressure drops and its requested outlet pressures.",
            id="a pressure that is not positive while the pipeline is solved",
        ),
        # With two settings the first one is tried before any is selected.
        pytest.param(
            False,
            2,
            [2.0, 12.0],
            "Pump pipeline 'A' gets a pressure that is not positive (-2.0 bara) in {second_period}. "
            "Check its pressure drops and its requested outlet pressures.",
            id="a pressure that is not positive while a setting is tried",
        ),
        # The pressure drop of 65 bar is above the requested outlet pressure of 60 bara. No pump problem covers
        # the pressure dropper, so it is run when the streams are read.
        pytest.param(
            True,
            1,
            [2.0, 65.0],
            "Pump pipeline 'A' gets a pressure that is not positive (-5.0 bara) in {second_period}. "
            "Check its pressure drops and its requested outlet pressures.",
            id="a pressure that is not positive after the last pump problem",
        ),
    ],
)
def test_rejects_a_pressure_drop_with_the_pipeline_and_the_period(
    periods,
    expression_evaluator,
    pump_chart,
    pump_unit_factory,
    make_pipeline_with_problems,
    make_simulation,
    make_pressure_drop_configuration,
    pressure_dropper_is_after_the_choke,
    number_of_settings,
    pressure_drops_bara,
    message,
):
    pump = create_pump_units(pump_unit_factory(pump_chart=pump_chart), has_choke=True)
    pressure_dropper = TimeSeriesPressureDropperProcessUnit()
    process_units = (
        [*pump.get_process_units(), pressure_dropper]
        if pressure_dropper_is_after_the_choke
        else [pressure_dropper, *pump.get_process_units()]
    )
    pump_pipeline, problems = make_pipeline_with_problems("A", process_units, [pump])
    expression_evaluator.variables["$var.pressure_drop"] = pressure_drops_bara
    simulation = make_simulation(
        [(pump_pipeline, problems)],
        rate_fractions=[1.0],
        process_configurations={
            pump_pipeline.get_id(): {pressure_dropper.get_id(): make_pressure_drop_configuration("$var.pressure_drop")}
        },
        number_of_settings=number_of_settings,
    )

    with pytest.raises(InvalidEcalcModelException, match=re.escape(message.format(second_period=periods[1]))):
        evaluate_pump_simulation(simulation, [pump_pipeline])
