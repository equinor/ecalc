import pytest

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesInletProcessUnit,
    TimeSeriesOutletProcessUnit,
    TimeSeriesPressureDropperProcessUnit,
    TimeSeriesTemperatureSetterProcessUnit,
)
from libecalc.ecalc_model.process.pump.pump_pipeline_solver_builder import build_pump_pipeline_solver
from tests.libecalc.ecalc_model.pump_units import create_pump_units, get_connection_out_of


def _no_inlet(pump_unit_factory):
    pump = create_pump_units(pump_unit_factory(), has_choke=True)
    return [*pump.get_process_units(), TimeSeriesOutletProcessUnit()], [pump.recirculation_loop], pump.choke, pump.choke


def _no_outlet(pump_unit_factory):
    pump = create_pump_units(pump_unit_factory(), has_choke=True)
    process_units = [TimeSeriesInletProcessUnit(), *pump.get_process_units(), TimeSeriesPressureDropperProcessUnit()]
    return process_units, [pump.recirculation_loop], pump.choke, pump.choke


def _two_pumps_in_one_problem(pump_unit_factory):
    first = create_pump_units(pump_unit_factory(), has_choke=False)
    second = create_pump_units(pump_unit_factory(), has_choke=True)
    process_units = [
        TimeSeriesInletProcessUnit(),
        *first.get_process_units(),
        *second.get_process_units(),
        TimeSeriesOutletProcessUnit(),
    ]
    return process_units, [first.recirculation_loop, second.recirculation_loop], second.choke, second.choke


def _pump_without_a_recirculation_loop(pump_unit_factory):
    pump = create_pump_units(pump_unit_factory(), has_choke=True)
    process_units = [TimeSeriesInletProcessUnit(), *pump.get_process_units(), TimeSeriesOutletProcessUnit()]
    return process_units, [], pump.choke, pump.choke


def _pressure_dropper_between_the_pump_and_its_splitter(pump_unit_factory):
    pump = create_pump_units(pump_unit_factory(), has_choke=True)
    process_units = [
        TimeSeriesInletProcessUnit(),
        pump.mixer,
        pump.pump,
        TimeSeriesPressureDropperProcessUnit(),
        pump.splitter,
        pump.choke,
        TimeSeriesOutletProcessUnit(),
    ]
    return process_units, [pump.recirculation_loop], pump.choke, pump.choke


def _choke_the_problem_does_not_name(pump_unit_factory):
    pump = create_pump_units(pump_unit_factory(), has_choke=True)
    process_units = [TimeSeriesInletProcessUnit(), *pump.get_process_units(), TimeSeriesOutletProcessUnit()]
    return process_units, [pump.recirculation_loop], pump.choke, None


def _choke_after_the_last_target(pump_unit_factory):
    pump = create_pump_units(pump_unit_factory(), has_choke=True)
    process_units = [
        TimeSeriesInletProcessUnit(),
        *pump.get_process_units(),
        TimeSeriesChokeProcessUnit(),
        TimeSeriesOutletProcessUnit(),
    ]
    return process_units, [pump.recirculation_loop], pump.choke, pump.choke


def _unit_with_no_liquid_unit(pump_unit_factory):
    pump = create_pump_units(pump_unit_factory(), has_choke=True)
    process_units = [
        TimeSeriesInletProcessUnit(),
        TimeSeriesTemperatureSetterProcessUnit(),
        *pump.get_process_units(),
        TimeSeriesOutletProcessUnit(),
    ]
    return process_units, [pump.recirculation_loop], pump.choke, pump.choke


@pytest.mark.parametrize(
    "create_case, message",
    [
        pytest.param(_no_inlet, "must start with an inlet and end with an outlet", id="no inlet first"),
        pytest.param(_no_outlet, "must start with an inlet and end with an outlet", id="no outlet last"),
        pytest.param(_two_pumps_in_one_problem, "pump problem '.*' must cover", id="two pumps in one problem"),
        pytest.param(
            _pump_without_a_recirculation_loop,
            "pump problem '.*' must cover",
            id="a pump without a recirculation loop",
        ),
        pytest.param(
            _pressure_dropper_between_the_pump_and_its_splitter,
            "pump problem '.*' must cover",
            id="a unit between the mixer and the target",
        ),
        pytest.param(
            _choke_the_problem_does_not_name,
            "pump problem '.*' must cover",
            id="a choke the problem does not name",
        ),
        pytest.param(
            _choke_after_the_last_target,
            "must have only pressure droppers between the target of its last pump problem and its outlet",
            id="a choke after the last target",
        ),
        pytest.param(
            _unit_with_no_liquid_unit,
            "'TimeSeriesTemperatureSetterProcessUnit', which has no liquid process unit",
            id="a unit with no liquid unit",
        ),
    ],
)
def test_rejects_a_pump_pipeline_the_solver_does_not_account_for(
    pump_unit_factory, pump_pipeline_factory, pump_problem_factory, create_case, message
):
    """Each case is one pump problem. ``create_case`` gives the process units, the recirculation loops, the
    target of the problem and the choke it names.

    What the builder accepts is what the YAML mapper builds, which ``test_pump_simulation_evaluation.py``
    evaluates.
    """
    process_units, recirculation_loops, target, named_choke = create_case(pump_unit_factory)
    pump_pipeline = pump_pipeline_factory(
        name="water_injection", process_units=process_units, recirculation_loops=recirculation_loops
    )
    problem = pump_problem_factory(
        pump_pipeline,
        target_process_unit_id=target.get_id(),
        target_process_connection_id=get_connection_out_of(pump_pipeline, target).get_id(),
        choke_pressure_control_id=named_choke.get_id() if named_choke is not None else None,
    )

    with pytest.raises(ProgrammingError, match=f"Pump pipeline 'water_injection' .*{message}"):
        build_pump_pipeline_solver(pump_pipeline, [problem])
