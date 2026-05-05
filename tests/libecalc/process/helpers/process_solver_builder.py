from __future__ import annotations

from collections.abc import Sequence
from typing import assert_never

from libecalc.ecalc_model.process_simulation import PressureControlConfig, PressureControlType
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.process_pipeline.process_pipeline import ProcessPipeline
from libecalc.process.process_pipeline.process_unit import ProcessUnit
from libecalc.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.process.process_solver.pressure_control.downstream_choke import DownstreamChokePressureControlStrategy
from libecalc.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.pressure_control.upstream_choke import UpstreamChokePressureControlStrategy
from libecalc.process.process_solver.process_pipeline_runner import ProcessPipelineRunner
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_solver.search_strategies import RootFindingStrategy, ScipyRootFindingStrategy
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.liquid_remover import LiquidRemover
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from libecalc.process.shaft import VariableSpeedShaft
from tests.libecalc.process.helpers.process_solver_system import ProcessSolverSystem, StageConfig


class ProcessSolverBuilder:
    """Build fully-wired process solver systems for tests.

    This mirrors the production process-simulation assembly without YAML,
    expressions, or time-series concerns.
    """

    def __init__(
        self,
        *,
        stages: Sequence[StageConfig],
        pressure_control_type: PressureControlType,
        fluid_service: FluidService,
        root_finding_strategy: RootFindingStrategy | None = None,
    ) -> None:
        if not stages:
            raise ValueError("At least one stage is required")
        self._stages = tuple(stages)
        self._pressure_control_config = PressureControlConfig(type=pressure_control_type)
        self._fluid_service = fluid_service
        self._root_finding_strategy = root_finding_strategy or ScipyRootFindingStrategy()

    def build(self) -> ProcessSolverSystem:
        shaft = VariableSpeedShaft()
        compressors: list[Compressor] = []
        stage_units = [
            self._create_stage_units(stage=stage, shaft=shaft, compressors=compressors) for stage in self._stages
        ]

        process_units, recirculation_loops = self._wrap_with_recirculation(stage_units=stage_units)
        choke: Choke | None = None
        choke_configuration_handler: ChokeConfigurationHandler | None = None
        configuration_handlers = [shaft, *recirculation_loops]

        if self._pressure_control_config.type in {"DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE"}:
            choke = Choke(fluid_service=self._fluid_service)
            choke_configuration_handler = ChokeConfigurationHandler(choke=choke)
            configuration_handlers.append(choke_configuration_handler)
            if self._pressure_control_config.type == "DOWNSTREAM_CHOKE":
                process_units = [*process_units, choke]
            else:
                process_units = [choke, *process_units]

        pipeline = ProcessPipeline(stream_propagators=process_units)
        runner = ProcessPipelineRunner(units=process_units, configuration_handlers=configuration_handlers)
        anti_surge_strategy = self._create_anti_surge_strategy(
            runner=runner,
            recirculation_loops=recirculation_loops,
            compressors=compressors,
        )
        pressure_control_strategy = self._create_pressure_control_strategy(
            runner=runner,
            recirculation_loops=recirculation_loops,
            compressors=compressors,
            choke_configuration_handler=choke_configuration_handler,
        )
        solver = OutletPressureSolver(
            shaft_id=shaft.get_id(),
            process_pipeline_id=pipeline.get_id(),
            runner=runner,
            anti_surge_strategy=anti_surge_strategy,
            pressure_control_strategy=pressure_control_strategy,
            root_finding_strategy=self._root_finding_strategy,
            speed_boundary=shaft.get_speed_boundary(),
        )

        return ProcessSolverSystem(
            solver=solver,
            runner=runner,
            pipeline=pipeline,
            shaft=shaft,
            compressors=tuple(compressors),
            recirculation_loops=tuple(recirculation_loops),
            choke=choke,
        )

    def _create_stage_units(
        self,
        *,
        stage: StageConfig,
        shaft: VariableSpeedShaft,
        compressors: list[Compressor],
    ) -> list[ProcessUnit]:
        compressor = Compressor(compressor_chart=stage.chart_data, fluid_service=self._fluid_service)
        shaft.connect(compressor)
        compressors.append(compressor)

        units: list[ProcessUnit] = [
            TemperatureSetter(
                required_temperature_kelvin=stage.inlet_temperature_kelvin,
                fluid_service=self._fluid_service,
            ),
            Choke(
                fluid_service=self._fluid_service,
                pressure_change=stage.pressure_drop_ahead_of_stage,
            ),
        ]
        if stage.remove_liquid_after_cooling:
            units.append(LiquidRemover(fluid_service=self._fluid_service))
        units.append(compressor)
        return units

    def _wrap_with_recirculation(
        self,
        *,
        stage_units: Sequence[Sequence[ProcessUnit]],
    ) -> tuple[list[ProcessUnit], list[RecirculationLoop]]:
        if self._pressure_control_config.type == "COMMON_ASV":
            recirculation_loop, process_units = self._wrap_units_with_asv(
                [unit for units in stage_units for unit in units]
            )
            return process_units, [recirculation_loop]

        process_units: list[ProcessUnit] = []
        recirculation_loops: list[RecirculationLoop] = []
        for units in stage_units:
            recirculation_loop, stage_process_units = self._wrap_units_with_asv(units)
            recirculation_loops.append(recirculation_loop)
            process_units.extend(stage_process_units)
        return process_units, recirculation_loops

    @staticmethod
    def _wrap_units_with_asv(units: Sequence[ProcessUnit]) -> tuple[RecirculationLoop, list[ProcessUnit]]:
        mixer = DirectMixer()
        splitter = DirectSplitter()
        recirculation_loop = RecirculationLoop(mixer=mixer, splitter=splitter)
        return recirculation_loop, [mixer, *units, splitter]

    def _create_anti_surge_strategy(
        self,
        *,
        runner: ProcessPipelineRunner,
        recirculation_loops: Sequence[RecirculationLoop],
        compressors: Sequence[Compressor],
    ) -> CommonASVAntiSurgeStrategy | IndividualASVAntiSurgeStrategy:
        match self._pressure_control_config.type:
            case "COMMON_ASV":
                return CommonASVAntiSurgeStrategy(
                    simulator=runner,
                    root_finding_strategy=self._root_finding_strategy,
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
                assert_never(self._pressure_control_config.type)

    def _create_pressure_control_strategy(
        self,
        *,
        runner: ProcessPipelineRunner,
        recirculation_loops: Sequence[RecirculationLoop],
        compressors: Sequence[Compressor],
        choke_configuration_handler: ChokeConfigurationHandler | None,
    ) -> PressureControlStrategy:
        match self._pressure_control_config.type:
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
                    root_finding_strategy=self._root_finding_strategy,
                )
            case "COMMON_ASV":
                return CommonASVPressureControlStrategy(
                    simulator=runner,
                    recirculation_loop_id=recirculation_loops[0].get_id(),
                    first_compressor=compressors[0],
                    root_finding_strategy=self._root_finding_strategy,
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
                    root_finding_strategy=self._root_finding_strategy,
                )
            case _:
                assert_never(self._pressure_control_config.type)
