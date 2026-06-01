"""Production solver assembly: wire physical components into a working solver.

This module contains the single source of truth for assembling an
OutletPressureSolver from its collaborating objects (runner, anti-surge
strategy, pressure control strategy).  Both the YAML mapper and test
infrastructure should use ``assemble_solver`` to ensure tests exercise
the same wiring logic as production.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import assert_never

from libecalc.common.ddd import value_object
from libecalc.process.process_pipeline.process_pipeline import ProcessPipeline
from libecalc.process.process_pipeline.process_unit import ProcessUnit
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.minimum_flow_protected_process_runner import MinimumFlowProtectedProcessRunner
from libecalc.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.process.process_solver.pressure_control.downstream_choke import DownstreamChokePressureControlStrategy
from libecalc.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import (
    PressureControlStrategy,
    PressureControlType,
)
from libecalc.process.process_solver.pressure_control.upstream_choke import UpstreamChokePressureControlStrategy
from libecalc.process.process_solver.process_pipeline_runner import ProcessPipelineRunner
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_solver.search_strategies import RootFindingStrategy, ScipyRootFindingStrategy
from libecalc.process.process_solver.speed_search import SpeedSearch
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.shaft import VariableSpeedShaft


@value_object
class ProcessSolverSystem:
    """A fully-wired solver with all its collaborating objects.

    Bundles the OutletPressureSolver together with the physical components
    it operates on, so callers can inspect topology and run the solver.
    """

    solver: OutletPressureSolver
    runner: ProcessRunner
    pipeline: ProcessPipeline
    shaft: VariableSpeedShaft
    compressors: tuple[Compressor, ...]
    recirculation_loops: tuple[RecirculationLoop, ...]
    choke: Choke | None


def assemble_solver(
    *,
    process_units: Sequence[ProcessUnit],
    configuration_handlers: Sequence[ConfigurationHandler],
    compressors: Sequence[Compressor],
    recirculation_loops: Sequence[RecirculationLoop],
    shaft: VariableSpeedShaft,
    pipeline_name: str,
    pressure_control_type: PressureControlType,
    choke: Choke | None = None,
    choke_configuration_handler: ChokeConfigurationHandler | None = None,
    root_finding_strategy: RootFindingStrategy | None = None,
) -> ProcessSolverSystem:
    """Assemble a fully-wired OutletPressureSolver from physical components.

    This is the production solver assembly path.  It creates the
    ProcessPipelineRunner, resolves the anti-surge and pressure control
    strategies from the ``pressure_control_type``, and wires everything
    into an OutletPressureSolver.

    Args:
        process_units: Ordered list of process units forming the pipeline
            (including mixers, splitters, compressors, choke, etc.).
        configuration_handlers: All configuration handlers for the runner
            (shaft, recirculation loops, choke handler).
        compressors: Compressor instances (for strategy wiring).
        recirculation_loops: Recirculation loops wrapping compressor stages.
        shaft: The variable-speed shaft connecting the compressors.
        pipeline_name: Name for the ProcessPipeline.
        pressure_control_type: Determines which anti-surge and pressure
            control strategies to instantiate.
        choke: The pressure-control choke (if any).  Included in the
            returned ProcessSolverSystem for inspection.
        choke_configuration_handler: Required for UPSTREAM_CHOKE and
            DOWNSTREAM_CHOKE modes.
        root_finding_strategy: Numerical solver strategy.  Defaults to
            ScipyRootFindingStrategy.
    """
    if root_finding_strategy is None:
        root_finding_strategy = ScipyRootFindingStrategy()

    pipeline = ProcessPipeline(name=pipeline_name, stream_propagators=process_units)
    runner = ProcessPipelineRunner(units=process_units, configuration_handlers=configuration_handlers)

    anti_surge_strategy = _resolve_anti_surge_strategy(
        pressure_control_type=pressure_control_type,
        runner=runner,
        compressors=compressors,
        recirculation_loops=recirculation_loops,
        root_finding_strategy=root_finding_strategy,
    )

    pressure_control_strategy = _resolve_pressure_control_strategy(
        pressure_control_type=pressure_control_type,
        runner=runner,
        compressors=compressors,
        recirculation_loops=recirculation_loops,
        choke_configuration_handler=choke_configuration_handler,
        anti_surge_strategy=anti_surge_strategy,
        root_finding_strategy=root_finding_strategy,
    )

    protected_runner = MinimumFlowProtectedProcessRunner(
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
    )

    speed_search = SpeedSearch(
        runner=protected_runner,
        shaft_id=shaft.get_id(),
        speed_boundary=shaft.get_speed_boundary(),
        root_finding_strategy=root_finding_strategy,
    )

    solver = OutletPressureSolver(
        shaft_id=shaft.get_id(),
        process_pipeline_id=pipeline.get_id(),
        runner=protected_runner,
        pressure_control_strategy=pressure_control_strategy,
        speed_search=speed_search,
    )

    return ProcessSolverSystem(
        solver=solver,
        runner=protected_runner,
        pipeline=pipeline,
        shaft=shaft,
        compressors=tuple(compressors),
        recirculation_loops=tuple(recirculation_loops),
        choke=choke,
    )


def _resolve_anti_surge_strategy(
    *,
    pressure_control_type: PressureControlType,
    runner: ProcessPipelineRunner,
    compressors: Sequence[Compressor],
    recirculation_loops: Sequence[RecirculationLoop],
    root_finding_strategy: RootFindingStrategy,
) -> AntiSurgeStrategy:
    """Resolve the anti-surge strategy from the pressure control type."""
    match pressure_control_type:
        case "COMMON_ASV":
            return CommonASVAntiSurgeStrategy(
                simulator=runner,
                root_finding_strategy=root_finding_strategy,
                first_compressor=compressors[0],
                recirculation_loop_id=recirculation_loops[0].get_id(),
            )
        case "DOWNSTREAM_CHOKE" | "UPSTREAM_CHOKE" | "INDIVIDUAL_ASV_RATE" | "INDIVIDUAL_ASV_PRESSURE":
            return IndividualASVAntiSurgeStrategy(
                simulator=runner,
                recirculation_loop_ids=[loop.get_id() for loop in recirculation_loops],
                compressors=compressors,
            )
        case _:
            assert_never(pressure_control_type)


def _resolve_pressure_control_strategy(
    *,
    pressure_control_type: PressureControlType,
    runner: ProcessPipelineRunner,
    compressors: Sequence[Compressor],
    recirculation_loops: Sequence[RecirculationLoop],
    choke_configuration_handler: ChokeConfigurationHandler | None,
    anti_surge_strategy: AntiSurgeStrategy,
    root_finding_strategy: RootFindingStrategy,
) -> PressureControlStrategy:
    """Resolve the pressure control strategy from the pressure control type."""
    match pressure_control_type:
        case "DOWNSTREAM_CHOKE":
            assert choke_configuration_handler is not None
            return DownstreamChokePressureControlStrategy(
                simulator=runner,
                choke_configuration_handler_id=choke_configuration_handler.get_id(),
            )
        case "UPSTREAM_CHOKE":
            assert choke_configuration_handler is not None
            return UpstreamChokePressureControlStrategy(
                simulator=runner,
                choke_configuration_handler_id=choke_configuration_handler.get_id(),
                root_finding_strategy=root_finding_strategy,
                anti_surge_strategy=anti_surge_strategy,
            )
        case "COMMON_ASV":
            return CommonASVPressureControlStrategy(
                simulator=runner,
                recirculation_loop_id=recirculation_loops[0].get_id(),
                first_compressor=compressors[0],
                root_finding_strategy=root_finding_strategy,
            )
        case "INDIVIDUAL_ASV_RATE":
            return IndividualASVRateControlStrategy(
                simulator=runner,
                recirculation_loop_ids=[loop.get_id() for loop in recirculation_loops],
                compressors=compressors,
            )
        case "INDIVIDUAL_ASV_PRESSURE":
            return IndividualASVPressureControlStrategy(
                simulator=runner,
                recirculation_loop_ids=[loop.get_id() for loop in recirculation_loops],
                compressors=compressors,
                root_finding_strategy=root_finding_strategy,
            )
        case _:
            assert_never(pressure_control_type)
