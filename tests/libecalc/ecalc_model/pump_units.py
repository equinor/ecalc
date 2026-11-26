from dataclasses import dataclass

from libecalc.ecalc_model.process.process_pipeline import ProcessUnitConnection
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesProcessUnit,
    TimeSeriesPumpProcessUnit,
)
from libecalc.ecalc_model.process.pump.liquid_recirculation_loop import LiquidRecirculationLoop
from libecalc.ecalc_model.process.pump.pump_pipeline import PumpPipeline
from libecalc.ecalc_model.process.pump.pump_simulation import PumpProblem
from libecalc.expression.expression import ExpressionType


@dataclass(frozen=True)
class PumpUnits:
    """A pump with the units and the recirculation loop the YAML mapper creates for it."""

    mixer: TimeSeriesDirectMixerProcessUnit
    pump: TimeSeriesPumpProcessUnit
    splitter: TimeSeriesDirectSplitterProcessUnit
    choke: TimeSeriesChokeProcessUnit | None
    recirculation_loop: LiquidRecirculationLoop

    def get_process_units(self) -> list[TimeSeriesProcessUnit]:
        process_units: list[TimeSeriesProcessUnit] = [self.mixer, self.pump, self.splitter]
        if self.choke is not None:
            process_units.append(self.choke)
        return process_units

    def get_target(self) -> TimeSeriesProcessUnit:
        """The unit the constraint of the pump is on: the choke, or the splitter when there is no choke."""
        return self.choke if self.choke is not None else self.splitter


def create_pump_units(pump: TimeSeriesPumpProcessUnit, has_choke: bool) -> PumpUnits:
    mixer = TimeSeriesDirectMixerProcessUnit()
    splitter = TimeSeriesDirectSplitterProcessUnit()
    return PumpUnits(
        mixer=mixer,
        pump=pump,
        splitter=splitter,
        choke=TimeSeriesChokeProcessUnit() if has_choke else None,
        recirculation_loop=LiquidRecirculationLoop(
            mixer_process_unit_id=mixer.get_id(), splitter_process_unit_id=splitter.get_id()
        ),
    )


def get_connection_out_of(pump_pipeline: PumpPipeline, process_unit: TimeSeriesProcessUnit) -> ProcessUnitConnection:
    [connection] = [
        connection
        for connection in pump_pipeline.get_process_unit_connections()
        if connection.get_from_process_unit_id() == process_unit.get_id()
    ]
    return connection


def create_pump_problem(
    pump_problem_factory, pump_pipeline: PumpPipeline, pump_units: PumpUnits, outlet_pressure: ExpressionType
) -> PumpProblem:
    """The pump problem of one pump, which names the pump's choke when it has one."""
    target = pump_units.get_target()
    return pump_problem_factory(
        pump_pipeline,
        outlet_pressure=outlet_pressure,
        target_process_unit_id=target.get_id(),
        target_process_connection_id=get_connection_out_of(pump_pipeline, target).get_id(),
        choke_pressure_control_id=pump_units.choke.get_id() if pump_units.choke is not None else None,
    )
