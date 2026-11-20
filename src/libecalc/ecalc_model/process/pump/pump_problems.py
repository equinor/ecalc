from collections.abc import Sequence

from libecalc.ecalc_model.process.process_units import TimeSeriesChokeProcessUnit, TimeSeriesPumpProcessUnit
from libecalc.ecalc_model.process.pump.pump_pipeline import PumpPipeline
from libecalc.ecalc_model.process.pump.pump_simulation import PumpProblem
from libecalc.ecalc_model.validation import InvalidEcalcModelException


def validate_pump_problems(pump_pipeline: PumpPipeline, pump_problems: Sequence[PumpProblem]) -> None:
    """
    Check that the pump problems, in flow order, split the pump pipeline so that every pump is solved by one problem.

    A problem covers the process units after the target of the previous problem (or from the inlet) up to and
    including its own target process unit.
    """
    subject = f"Pump pipeline '{pump_pipeline.get_name()}'"
    process_units = pump_pipeline.get_process_units()
    unit_index_by_id = {process_unit.get_id(): index for index, process_unit in enumerate(process_units)}
    connection_by_id = {connection.get_id(): connection for connection in pump_pipeline.get_process_unit_connections()}

    if not pump_problems:
        raise InvalidEcalcModelException(f"{subject} must have at least one pump problem.")

    start = 0
    for problem in pump_problems:
        if problem.get_pump_pipeline_id() != pump_pipeline.get_id():
            raise InvalidEcalcModelException(
                f"{subject} got pump problem '{problem.get_id()}' for another pump pipeline "
                f"'{problem.get_pump_pipeline_id()}'."
            )
        constraint = problem.get_constraint()
        connection = connection_by_id.get(constraint.target_process_connection_id)
        if connection is None or connection.get_from_process_unit_id() != constraint.target_process_unit_id:
            raise InvalidEcalcModelException(
                f"{subject} pump problem '{problem.get_id()}' must target a process unit in the pipeline and the "
                "connection out of it."
            )
        end = unit_index_by_id[constraint.target_process_unit_id]
        if end < start:
            raise InvalidEcalcModelException(
                f"{subject} pump problems must be given in flow order, each targeting a process unit downstream of "
                "the previous target."
            )
        problem_units = process_units[start : end + 1]
        if not any(isinstance(process_unit, TimeSeriesPumpProcessUnit) for process_unit in problem_units):
            raise InvalidEcalcModelException(
                f"{subject} pump problem '{problem.get_id()}' must cover at least one pump."
            )
        choke_id = problem.get_choke_pressure_control_id()
        if choke_id is not None and not any(
            isinstance(process_unit, TimeSeriesChokeProcessUnit) and process_unit.get_id() == choke_id
            for process_unit in problem_units
        ):
            raise InvalidEcalcModelException(
                f"{subject} pump problem '{problem.get_id()}' choke pressure control '{choke_id}' must be a choke "
                "covered by the problem."
            )
        start = end + 1

    if any(isinstance(process_unit, TimeSeriesPumpProcessUnit) for process_unit in process_units[start:]):
        raise InvalidEcalcModelException(
            f"{subject} has pumps downstream of its last pump problem target. Every pump must be covered by a pump "
            "problem."
        )
