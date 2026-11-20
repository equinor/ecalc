import pytest

from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesInletProcessUnit,
    TimeSeriesOutletProcessUnit,
)
from libecalc.ecalc_model.process.pump.pump_problems import validate_pump_problems
from libecalc.ecalc_model.validation import InvalidEcalcModelException


@pytest.fixture
def two_pump_pipeline(pump_pipeline_factory, pump_unit_factory):
    return pump_pipeline_factory(
        process_units=[
            TimeSeriesInletProcessUnit(),
            pump_unit_factory(),
            TimeSeriesChokeProcessUnit(),
            pump_unit_factory(),
            TimeSeriesChokeProcessUnit(),
            TimeSeriesOutletProcessUnit(),
        ]
    )


@pytest.fixture
def problem_at(pump_problem_factory):
    def create(pump_pipeline, unit_index: int, **kwargs):
        unit = pump_pipeline.get_process_units()[unit_index]
        connection = pump_pipeline.get_process_unit_connections()[unit_index]
        return pump_problem_factory(
            pump_pipeline,
            target_process_unit_id=unit.get_id(),
            target_process_connection_id=connection.get_id(),
            **kwargs,
        )

    return create


def test_one_problem_per_pump(two_pump_pipeline, problem_at):
    first_choke, second_choke = two_pump_pipeline.get_process_units()[2], two_pump_pipeline.get_process_units()[4]

    validate_pump_problems(
        two_pump_pipeline,
        [
            problem_at(two_pump_pipeline, 2, choke_pressure_control_id=first_choke.get_id()),
            problem_at(two_pump_pipeline, 4, choke_pressure_control_id=second_choke.get_id()),
        ],
    )


def test_one_problem_may_cover_several_pumps(two_pump_pipeline, problem_at):
    validate_pump_problems(two_pump_pipeline, [problem_at(two_pump_pipeline, 4)])


def test_requires_a_problem(two_pump_pipeline):
    with pytest.raises(InvalidEcalcModelException, match="at least one pump problem"):
        validate_pump_problems(two_pump_pipeline, [])


def test_rejects_pump_after_last_target(two_pump_pipeline, problem_at):
    with pytest.raises(InvalidEcalcModelException, match="pumps downstream of its last pump problem target"):
        validate_pump_problems(two_pump_pipeline, [problem_at(two_pump_pipeline, 2)])


def test_rejects_problem_without_pump(two_pump_pipeline, problem_at):
    with pytest.raises(InvalidEcalcModelException, match="must cover at least one pump"):
        validate_pump_problems(two_pump_pipeline, [problem_at(two_pump_pipeline, 0), problem_at(two_pump_pipeline, 4)])


def test_rejects_problems_out_of_flow_order(two_pump_pipeline, problem_at):
    with pytest.raises(InvalidEcalcModelException, match="flow order"):
        validate_pump_problems(two_pump_pipeline, [problem_at(two_pump_pipeline, 4), problem_at(two_pump_pipeline, 2)])


def test_rejects_target_not_in_pipeline(two_pump_pipeline, pump_pipeline_factory, problem_at):
    other_pipeline = pump_pipeline_factory()
    problem = problem_at(other_pipeline, 4)

    with pytest.raises(InvalidEcalcModelException, match="for another pump pipeline"):
        validate_pump_problems(two_pump_pipeline, [problem])


def test_rejects_connection_not_out_of_target(two_pump_pipeline, pump_problem_factory):
    units = two_pump_pipeline.get_process_units()
    connections = two_pump_pipeline.get_process_unit_connections()
    problem = pump_problem_factory(
        two_pump_pipeline,
        target_process_unit_id=units[4].get_id(),
        target_process_connection_id=connections[2].get_id(),
    )

    with pytest.raises(InvalidEcalcModelException, match="the connection out of it"):
        validate_pump_problems(two_pump_pipeline, [problem])


def test_rejects_choke_pressure_control_outside_problem(two_pump_pipeline, problem_at):
    second_choke = two_pump_pipeline.get_process_units()[4]

    with pytest.raises(InvalidEcalcModelException, match="must be a choke covered by the problem"):
        validate_pump_problems(
            two_pump_pipeline,
            [
                problem_at(two_pump_pipeline, 2, choke_pressure_control_id=second_choke.get_id()),
                problem_at(two_pump_pipeline, 4),
            ],
        )


def test_problem_without_choke_may_target_the_splitter(pump_pipeline_factory, pump_unit_factory, problem_at):
    pump_pipeline = pump_pipeline_factory(
        process_units=[
            TimeSeriesInletProcessUnit(),
            TimeSeriesDirectMixerProcessUnit(),
            pump_unit_factory(),
            TimeSeriesDirectSplitterProcessUnit(),
            TimeSeriesOutletProcessUnit(),
        ]
    )

    validate_pump_problems(pump_pipeline, [problem_at(pump_pipeline, 3)])
