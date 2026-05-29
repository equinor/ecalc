from __future__ import annotations

from collections.abc import Sequence

from libecalc.ecalc_model.process_simulation import PressureControlConfig, PressureControlType
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.process_pipeline.process_unit import ProcessUnit
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_solver.search_strategies import RootFindingStrategy, ScipyRootFindingStrategy
from libecalc.process.process_solver.solver_assembly import ProcessSolverSystem, assemble_solver
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.liquid_remover import LiquidRemover
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from libecalc.process.shaft import VariableSpeedShaft
from tests.libecalc.process.helpers.process_solver_system import StageConfig


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

        return assemble_solver(
            process_units=process_units,
            configuration_handlers=configuration_handlers,
            compressors=compressors,
            recirculation_loops=recirculation_loops,
            shaft=shaft,
            pipeline_name="test-pipeline",
            pressure_control_type=self._pressure_control_config.type,
            choke=choke,
            choke_configuration_handler=choke_configuration_handler,
            root_finding_strategy=self._root_finding_strategy,
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
