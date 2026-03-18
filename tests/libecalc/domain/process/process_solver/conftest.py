import pytest

from libecalc.domain.process.entities.shaft import Shaft, VariableSpeedShaft
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.asv_solvers import ASVSolver
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.domain.process.process_solver.pressure_control.downstream_choke import (
    DownstreamChokePressureControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.pressure_control.upstream_choke import UpstreamChokePressureControlStrategy
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.process_system.process_system import ProcessSystemId
from libecalc.domain.process.process_system.process_unit import ProcessUnitId, create_process_unit_id
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class SpeedCompressorStage(CompressorStageProcessUnit):
    """
    Test double that makes speed->pressure mapping deterministic:

      outlet_pressure = inlet_pressure + shaft_speed

    The capacity-related methods are implemented with wide limits to avoid
    interfering with tests that focus on solver orchestration.
    """

    def __init__(self, shaft: VariableSpeedShaft, fluid_service: FluidService):
        self._id = create_process_unit_id()
        self._shaft = shaft
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    def get_speed_boundary(self) -> Boundary:
        return Boundary(min=200.0, max=600.0)

    def get_maximum_standard_rate(self, inlet_stream: FluidStream) -> float:
        # "Infinite" capacity for test purposes
        return 1e30

    def get_minimum_standard_rate(self, inlet_stream: FluidStream) -> float:
        # "No minimum" for test purposes
        return 0.0

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        speed = self._shaft.get_speed()
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + speed,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )


@pytest.fixture
def speed_compressor_stage_factory(fluid_service):
    def create(shaft: VariableSpeedShaft):
        return SpeedCompressorStage(shaft=shaft, fluid_service=fluid_service)

    return create


@pytest.fixture
def outlet_pressure_solver_factory(root_finding_strategy):
    def create_outlet_pressure_solver(
        shaft: Shaft,
        runner: ProcessRunner,
        anti_surge_strategy: AntiSurgeStrategy,
        pressure_control_strategy: PressureControlStrategy,
        speed_boundary: Boundary,
    ):
        return ASVSolver(
            shaft=shaft,
            runner=runner,
            anti_surge_strategy=anti_surge_strategy,
            pressure_control_strategy=pressure_control_strategy,
            root_finding_strategy=root_finding_strategy,
            speed_boundary=speed_boundary,
        )

    return create_outlet_pressure_solver


@pytest.fixture
def common_asv_anti_surge_strategy_factory(root_finding_strategy):
    def create(
        runner: ProcessRunner,
        recirculation_loop_id: ProcessSystemId,
        first_compressor: CompressorStageProcessUnit,
    ) -> CommonASVAntiSurgeStrategy:
        return CommonASVAntiSurgeStrategy(
            simulator=runner,
            recirculation_loop_id=recirculation_loop_id,
            first_compressor=first_compressor,
            root_finding_strategy=root_finding_strategy,
        )

    return create


@pytest.fixture
def individual_asv_anti_surge_strategy_factory():
    def create(
        runner: ProcessRunner,
        recirculation_loop_ids: list[ProcessSystemId],
        compressors: list[CompressorStageProcessUnit],
    ) -> IndividualASVAntiSurgeStrategy:
        return IndividualASVAntiSurgeStrategy(
            recirculation_loop_ids=recirculation_loop_ids,
            compressors=compressors,
            simulator=runner,
        )

    return create


@pytest.fixture
def common_asv_pressure_control_strategy_factory(root_finding_strategy):
    def create(
        runner: ProcessRunner,
        recirculation_loop_id: ProcessSystemId,
        first_compressor: CompressorStageProcessUnit,
    ) -> CommonASVPressureControlStrategy:
        return CommonASVPressureControlStrategy(
            simulator=runner,
            recirculation_loop_id=recirculation_loop_id,
            first_compressor=first_compressor,
            root_finding_strategy=root_finding_strategy,
        )

    return create


@pytest.fixture
def individual_asv_rate_control_strategy_factory():
    def create(
        runner: ProcessRunner,
        recirculation_loop_ids: list[ProcessSystemId],
        compressors: list[CompressorStageProcessUnit],
    ) -> IndividualASVRateControlStrategy:
        return IndividualASVRateControlStrategy(
            simulator=runner,
            recirculation_loop_ids=recirculation_loop_ids,
            compressors=compressors,
        )

    return create


@pytest.fixture
def individual_asv_pressure_control_strategy_factory(root_finding_strategy):
    def create(
        runner: ProcessRunner,
        recirculation_loop_ids: list[ProcessSystemId],
        compressors: list[CompressorStageProcessUnit],
    ) -> IndividualASVPressureControlStrategy:
        return IndividualASVPressureControlStrategy(
            simulator=runner,
            recirculation_loop_ids=recirculation_loop_ids,
            compressors=compressors,
            root_finding_strategy=root_finding_strategy,
        )

    return create


@pytest.fixture
def upstream_choke_pressure_control_strategy_factory(root_finding_strategy):
    def create(
        runner: ProcessRunner,
        choke_id: ProcessUnitId,
    ) -> UpstreamChokePressureControlStrategy:
        return UpstreamChokePressureControlStrategy(
            simulator=runner,
            choke_id=choke_id,
            root_finding_strategy=root_finding_strategy,
        )

    return create


@pytest.fixture
def downstream_choke_pressure_control_strategy_factory():
    def create(
        runner: ProcessRunner,
        choke_id: ProcessUnitId,
    ) -> DownstreamChokePressureControlStrategy:
        return DownstreamChokePressureControlStrategy(
            simulator=runner,
            choke_id=choke_id,
        )

    return create
