from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from math import isnan

import numpy as np
import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.core.results.compressor import CompressorTrainCommonShaftFailureStatus
from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_pipeline.process_error import RateTooHighError
from libecalc.domain.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.domain.process.process_pipeline.process_unit import ProcessUnit
from libecalc.domain.process.process_solver.configuration import (
    ChokeConfiguration,
    Configuration,
    OperatingConfiguration,
    RecirculationConfiguration,
    SpeedConfiguration,
)
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.solver import (
    OutsideCapacityEvent,
    Solution,
    SolverFailureStatus,
    TargetNotAchievableEvent,
)
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.fluid_stream import FluidComposition, FluidStream
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidModel

PRESSURE_TOLERANCE = 1e-3
POWER_TOLERANCE = 0.1
RECIRCULATION_TOLERANCE = 1e-6


class SolverPathMode(StrEnum):
    NONE = "none"
    DOWNSTREAM_CHOKE = "downstream_choke"
    UPSTREAM_CHOKE = "upstream_choke"
    INDIVIDUAL_ASV_RATE = "individual_asv_rate"
    INDIVIDUAL_ASV_PRESSURE = "individual_asv_pressure"
    COMMON_ASV = "common_asv"


class PressureExpectation(StrEnum):
    TARGET = "target"
    ABOVE_TARGET = "above_target"
    BELOW_TARGET = "below_target"
    NOT_ASSERTED = "not_asserted"
    NAN = "nan"


class SpeedBoundaryClass(StrEnum):
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    INTERNAL = "internal"
    NOT_ASSERTED = "not_asserted"


@dataclass(frozen=True)
class SolverRegion:
    id: str
    rate_sm3_day: float
    suction_pressure_bara: float
    discharge_pressure_bara: float
    speed_boundary_class: SpeedBoundaryClass
    pressure_expectation_when_invalid: PressureExpectation
    expected_chart_area: ChartAreaFlag | None = None
    expect_auto_anti_surge: bool = False


@dataclass(frozen=True)
class CellExpectation:
    success: bool
    failure_status: CompressorTrainCommonShaftFailureStatus
    power_mw: float
    pressure_expectation: PressureExpectation
    expect_pressure_control: bool = False
    expect_pressure_control_recirculation: bool = False
    expect_downstream_choke: bool = False
    expect_upstream_choke: bool = False


@dataclass(frozen=True)
class MatrixCell:
    region: SolverRegion
    mode: SolverPathMode
    expectation: CellExpectation

    @property
    def id(self) -> str:
        return f"{self.region.id}-{self.mode.value}"


@dataclass(frozen=True)
class MatrixObservation:
    is_valid: bool
    failure_status: CompressorTrainCommonShaftFailureStatus
    outlet_pressure_bara: float
    speed: float
    power_mw: float | None
    chart_area_flag: ChartAreaFlag | None
    recirculation_rates: tuple[float, ...]
    anti_surge_recirculation_rates: tuple[float, ...]
    choke_delta_pressure: float | None
    suction_pressure_after_upstream_choke_bara: float | None

    @property
    def has_recirculation(self) -> bool:
        return any(rate > RECIRCULATION_TOLERANCE for rate in self.recirculation_rates)

    @property
    def has_anti_surge_recirculation(self) -> bool:
        return any(rate > RECIRCULATION_TOLERANCE for rate in self.anti_surge_recirculation_rates)


REGIONS = {
    "R1": SolverRegion(
        id="R1",
        rate_sm3_day=5_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=100.0,
        speed_boundary_class=SpeedBoundaryClass.INTERNAL,
        pressure_expectation_when_invalid=PressureExpectation.NOT_ASSERTED,
        expected_chart_area=ChartAreaFlag.INTERNAL_POINT,
    ),
    "R2": SolverRegion(
        id="R2",
        rate_sm3_day=2_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=90.0,
        speed_boundary_class=SpeedBoundaryClass.INTERNAL,
        pressure_expectation_when_invalid=PressureExpectation.NOT_ASSERTED,
        expected_chart_area=ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
        expect_auto_anti_surge=True,
    ),
    "R3": SolverRegion(
        id="R3",
        rate_sm3_day=500_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=60.0,
        speed_boundary_class=SpeedBoundaryClass.MINIMUM,
        pressure_expectation_when_invalid=PressureExpectation.ABOVE_TARGET,
        expected_chart_area=ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
        expect_auto_anti_surge=True,
    ),
    "R4": SolverRegion(
        id="R4",
        rate_sm3_day=5_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=200.0,
        speed_boundary_class=SpeedBoundaryClass.MAXIMUM,
        pressure_expectation_when_invalid=PressureExpectation.BELOW_TARGET,
    ),
    "R5": SolverRegion(
        id="R5",
        rate_sm3_day=15_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=50.0,
        speed_boundary_class=SpeedBoundaryClass.MAXIMUM,
        pressure_expectation_when_invalid=PressureExpectation.NOT_ASSERTED,
        expected_chart_area=ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
    ),
    "R6": SolverRegion(
        id="R6",
        rate_sm3_day=5_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=108.0,
        speed_boundary_class=SpeedBoundaryClass.INTERNAL,
        pressure_expectation_when_invalid=PressureExpectation.NOT_ASSERTED,
        expected_chart_area=ChartAreaFlag.INTERNAL_POINT,
    ),
    "R7": SolverRegion(
        id="R7",
        rate_sm3_day=3_500_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=62.0,
        speed_boundary_class=SpeedBoundaryClass.MINIMUM,
        pressure_expectation_when_invalid=PressureExpectation.ABOVE_TARGET,
        expected_chart_area=ChartAreaFlag.INTERNAL_POINT,
    ),
    "R8": SolverRegion(
        id="R8",
        rate_sm3_day=0.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=100.0,
        speed_boundary_class=SpeedBoundaryClass.NOT_ASSERTED,
        pressure_expectation_when_invalid=PressureExpectation.NAN,
        expected_chart_area=ChartAreaFlag.NOT_CALCULATED,
    ),
    "R9": SolverRegion(
        id="R9",
        rate_sm3_day=4_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=45.0,
        speed_boundary_class=SpeedBoundaryClass.MINIMUM,
        pressure_expectation_when_invalid=PressureExpectation.ABOVE_TARGET,
        expected_chart_area=ChartAreaFlag.INTERNAL_POINT,
    ),
}

MODES = tuple(SolverPathMode)

POWER_MW = {
    "R1": dict.fromkeys(MODES, 8.231),
    "R2": dict.fromkeys(MODES, 5.283),
    "R3": {
        SolverPathMode.NONE: 2.492,
        SolverPathMode.DOWNSTREAM_CHOKE: 2.492,
        SolverPathMode.UPSTREAM_CHOKE: 2.227,
        SolverPathMode.INDIVIDUAL_ASV_RATE: 2.967,
        SolverPathMode.INDIVIDUAL_ASV_PRESSURE: 2.967,
        SolverPathMode.COMMON_ASV: 2.967,
    },
    "R4": dict.fromkeys(MODES, 9.288),
    "R5": dict.fromkeys(MODES, 22.47),
    "R6": dict.fromkeys(MODES, 9.053),
    "R7": {
        SolverPathMode.NONE: 2.824,
        SolverPathMode.DOWNSTREAM_CHOKE: 2.824,
        SolverPathMode.UPSTREAM_CHOKE: 2.767,
        SolverPathMode.INDIVIDUAL_ASV_RATE: 2.945,
        SolverPathMode.INDIVIDUAL_ASV_PRESSURE: 2.945,
        SolverPathMode.COMMON_ASV: 2.945,
    },
    "R8": dict.fromkeys(MODES, 0.0),
    "R9": {
        SolverPathMode.NONE: 2.950,
        SolverPathMode.DOWNSTREAM_CHOKE: 2.950,
        SolverPathMode.UPSTREAM_CHOKE: 2.697,
        SolverPathMode.INDIVIDUAL_ASV_RATE: 2.964,
        SolverPathMode.INDIVIDUAL_ASV_PRESSURE: 2.964,
        SolverPathMode.COMMON_ASV: 4.456,
    },
}


def _expected_cell(region: SolverRegion, mode: SolverPathMode) -> CellExpectation:
    success = True
    failure_status = CompressorTrainCommonShaftFailureStatus.NO_FAILURE
    pressure_expectation = PressureExpectation.TARGET
    expect_pressure_control = False
    expect_pressure_control_recirculation = False
    expect_downstream_choke = False
    expect_upstream_choke = False

    if region.id in {"R4", "R5"}:
        success = False
        failure_status = (
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH
            if region.id == "R4"
            else CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE
        )
        pressure_expectation = region.pressure_expectation_when_invalid
    elif region.id in {"R3", "R7"}:
        expect_pressure_control = mode is not SolverPathMode.NONE
        if mode is SolverPathMode.NONE:
            success = False
            failure_status = CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW
            pressure_expectation = region.pressure_expectation_when_invalid
        elif mode is SolverPathMode.DOWNSTREAM_CHOKE:
            expect_downstream_choke = True
        elif mode is SolverPathMode.UPSTREAM_CHOKE:
            expect_upstream_choke = True
        else:
            expect_pressure_control_recirculation = True
    elif region.id == "R8":
        pressure_expectation = PressureExpectation.NAN
    elif region.id == "R9":
        expect_pressure_control = mode is not SolverPathMode.NONE
        if mode is SolverPathMode.NONE:
            success = False
            failure_status = CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW
            pressure_expectation = region.pressure_expectation_when_invalid
        elif mode is SolverPathMode.DOWNSTREAM_CHOKE:
            expect_downstream_choke = True
        elif mode is SolverPathMode.UPSTREAM_CHOKE:
            success = False
            failure_status = CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE
            pressure_expectation = PressureExpectation.NOT_ASSERTED
            expect_upstream_choke = True
        else:
            success = False
            failure_status = (
                CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE
                if mode is SolverPathMode.COMMON_ASV
                else CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW
            )
            pressure_expectation = PressureExpectation.NOT_ASSERTED
            expect_pressure_control_recirculation = mode is not SolverPathMode.COMMON_ASV

    return CellExpectation(
        success=success,
        failure_status=failure_status,
        power_mw=POWER_MW[region.id][mode],
        pressure_expectation=pressure_expectation,
        expect_pressure_control=expect_pressure_control,
        expect_pressure_control_recirculation=expect_pressure_control_recirculation,
        expect_downstream_choke=expect_downstream_choke,
        expect_upstream_choke=expect_upstream_choke,
    )


MATRIX_CELLS = tuple(
    MatrixCell(region=region, mode=mode, expectation=_expected_cell(region, mode))
    for region in REGIONS.values()
    for mode in MODES
)

PROCESS_XFAILS = (
    {
        (
            "R1",
            mode,
        ): "New SpeedSolver does not currently converge when the min-speed point is above stonewall before searching up to the feasible speed."
        for mode in MODES
    }
    | {
        (
            "R6",
            mode,
        ): "New SpeedSolver does not currently converge near the high-speed boundary when the min-speed point is above stonewall."
        for mode in MODES
    }
    | {
        ("R8", mode): "New process-domain solver does not currently implement the legacy zero-rate short-circuit."
        for mode in MODES
    }
    | {
        (
            "R5",
            SolverPathMode.NONE,
        ): "Common-ASV/new-process topology currently loses the flow-capacity failure event for this stonewall case.",
        (
            "R5",
            SolverPathMode.DOWNSTREAM_CHOKE,
        ): "Common-ASV/new-process topology currently loses the flow-capacity failure event for this stonewall case.",
        (
            "R5",
            SolverPathMode.UPSTREAM_CHOKE,
        ): "Common-ASV/new-process topology currently loses the flow-capacity failure event for this stonewall case.",
        (
            "R5",
            SolverPathMode.COMMON_ASV,
        ): "Common-ASV/new-process topology currently loses the flow-capacity failure event for this stonewall case.",
        (
            "R9",
            SolverPathMode.UPSTREAM_CHOKE,
        ): "New upstream-choke strategy currently reports success for the R9 stonewall-limited over-compression case.",
        (
            "R9",
            SolverPathMode.COMMON_ASV,
        ): "New common-ASV strategy reports a pressure-limit failure where legacy reports stonewall for R9.",
    }
)

PROCESS_MATRIX_PARAMS = tuple(
    pytest.param(
        cell,
        id=cell.id,
        marks=pytest.mark.xfail(reason=PROCESS_XFAILS[(cell.region.id, cell.mode)], strict=True),
    )
    if (cell.region.id, cell.mode) in PROCESS_XFAILS
    else pytest.param(cell, id=cell.id)
    for cell in MATRIX_CELLS
)

PRESSURE_CONTROL_BY_MODE = {
    SolverPathMode.NONE: None,
    SolverPathMode.DOWNSTREAM_CHOKE: FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
    SolverPathMode.UPSTREAM_CHOKE: FixedSpeedPressureControl.UPSTREAM_CHOKE,
    SolverPathMode.INDIVIDUAL_ASV_RATE: FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE,
    SolverPathMode.INDIVIDUAL_ASV_PRESSURE: FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
    SolverPathMode.COMMON_ASV: FixedSpeedPressureControl.COMMON_ASV,
}


class NoPressureControlStrategy(PressureControlStrategy):
    def __init__(self, runner: ProcessRunner, process_pipeline_id: ProcessPipelineId):
        self._runner = runner
        self._process_pipeline_id = process_pipeline_id

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[OperatingConfiguration]]]:
        try:
            outlet_stream = self._runner.run(inlet_stream=inlet_stream)
        except RateTooHighError as error:
            return Solution(
                success=False,
                configuration=[],
                failure_event=OutsideCapacityEvent(
                    status=SolverFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
                    actual_value=error.actual_rate,
                    boundary_value=error.boundary_rate,
                    source_id=error.process_unit_id,
                ),
            )

        if outlet_stream.pressure_bara == target_pressure:
            return Solution(success=True, configuration=[])

        status = (
            SolverFailureStatus.MINIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_ABOVE_TARGET
            if outlet_stream.pressure_bara > target_pressure.value
            else SolverFailureStatus.MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET
        )
        return Solution(
            success=False,
            configuration=[],
            failure_event=TargetNotAchievableEvent(
                status=status,
                achievable_value=outlet_stream.pressure_bara,
                target_value=target_pressure.value,
                source_id=self._process_pipeline_id,
            ),
        )


@pytest.fixture
def pure_methane_fluid_model(fluid_model_factory) -> FluidModel:
    return fluid_model_factory(
        fluid_composition=FluidComposition(
            water=0.0,
            nitrogen=0.0,
            CO2=0.0,
            methane=1.0,
            ethane=0.0,
            propane=0.0,
            i_butane=0.0,
            n_butane=0.0,
            i_pentane=0.0,
            n_pentane=0.0,
            n_hexane=0.0,
        ),
        eos_model=EoSModel.SRK,
    )


@pytest.fixture
def legacy_train_factory(compressor_stage_factory, fluid_service, pure_methane_fluid_model):
    def create_legacy_train(
        chart_data: ChartData,
        pressure_control: FixedSpeedPressureControl | None,
    ) -> CompressorTrainCommonShaft:
        shaft = VariableSpeedShaft()
        stage: CompressorTrainStage = compressor_stage_factory(
            shaft=shaft,
            compressor_chart_data=chart_data,
            inlet_temperature_kelvin=303.15,
            remove_liquid_after_cooling=True,
            pressure_drop_ahead_of_stage=0.0,
        )
        train = CompressorTrainCommonShaft(
            shaft=shaft,
            fluid_service=fluid_service,
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1,
            stages=[stage],
            pressure_control=pressure_control,
            calculate_max_rate=False,
        )
        train._fluid_model = [pure_methane_fluid_model]
        return train

    return create_legacy_train


def _legacy_observation(train: CompressorTrainCommonShaft, cell: MatrixCell) -> MatrixObservation:
    result = train.evaluate_given_constraints(
        CompressorTrainEvaluationInput(
            rates=[cell.region.rate_sm3_day],
            suction_pressure=cell.region.suction_pressure_bara,
            discharge_pressure=cell.region.discharge_pressure_bara,
        )
    )
    stage_result = result.stage_results[0]
    recirculation_rate = _safe_delta(
        stage_result.standard_rate_asv_corrected_sm3_per_day,
        stage_result.standard_rate_sm3_per_day,
    )
    speed = result.speed if not isnan(result.speed) else train.shaft.get_speed()
    return MatrixObservation(
        is_valid=result.is_valid,
        failure_status=result.failure_status,
        outlet_pressure_bara=result.discharge_pressure,
        speed=speed,
        power_mw=result.power_megawatt,
        chart_area_flag=result.chart_area_status,
        recirculation_rates=(recirculation_rate,),
        anti_surge_recirculation_rates=(recirculation_rate,) if cell.region.expect_auto_anti_surge else (),
        choke_delta_pressure=None,
        suction_pressure_after_upstream_choke_bara=_safe_pressure(stage_result.inlet_stream),
    )


def _safe_delta(left: float, right: float) -> float:
    if isnan(left) or isnan(right):
        return 0.0
    return left - right


def _safe_pressure(stream: FluidStream | None) -> float | None:
    if stream is None:
        return None
    return stream.pressure_bara


def _status_from_process_solution(
    solution: Solution[Sequence[Configuration]],
) -> CompressorTrainCommonShaftFailureStatus:
    if solution.success:
        return CompressorTrainCommonShaftFailureStatus.NO_FAILURE

    failure_event = solution.failure_event
    if failure_event is None:
        return CompressorTrainCommonShaftFailureStatus.NOT_CALCULATED

    if failure_event.status is SolverFailureStatus.ABOVE_MAXIMUM_FLOW_RATE:
        return CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE
    if failure_event.status is SolverFailureStatus.BELOW_MINIMUM_FLOW_RATE:
        return CompressorTrainCommonShaftFailureStatus.BELOW_MINIMUM_FLOW_RATE
    if failure_event.status is SolverFailureStatus.MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET:
        return CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH
    if failure_event.status is SolverFailureStatus.MINIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_ABOVE_TARGET:
        return CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW

    raise AssertionError(f"Unexpected process failure status: {failure_event.status}")


@dataclass(frozen=True)
class ProcessSolverSystem:
    solver: OutletPressureSolver
    runner: ProcessRunner
    inlet_stream: FluidStream
    shaft: VariableSpeedShaft
    recirculation_loops: tuple[RecirculationLoop, ...]
    choke: Choke | None


def _build_common_asv_units(
    *,
    stage_units: list[ProcessUnit],
    compressor: Compressor,
    shaft: VariableSpeedShaft,
    with_common_asv,
    process_runner_factory,
    common_asv_anti_surge_strategy_factory,
    configuration_handlers: list,
    extra_units_before: Sequence[ProcessUnit] = (),
    extra_units_after: Sequence[ProcessUnit] = (),
):
    recirculation_loop, process_units = with_common_asv(stage_units)
    all_process_units = [*extra_units_before, *process_units, *extra_units_after]
    runner = process_runner_factory(
        units=all_process_units,
        configuration_handlers=[shaft, recirculation_loop, *configuration_handlers],
    )
    anti_surge_strategy = common_asv_anti_surge_strategy_factory(
        runner=runner,
        recirculation_loop_id=recirculation_loop.get_id(),
        first_compressor=compressor,
    )
    return runner, anti_surge_strategy, (recirculation_loop,), all_process_units


@pytest.fixture
def process_solver_system_factory(
    stream_factory,
    compressor_factory,
    stage_units_factory,
    with_common_asv,
    with_individual_asv,
    process_pipeline_factory,
    process_runner_factory,
    choke_factory,
    choke_configuration_handler_factory,
    common_asv_anti_surge_strategy_factory,
    individual_asv_anti_surge_strategy_factory,
    downstream_choke_pressure_control_strategy_factory,
    upstream_choke_pressure_control_strategy_factory,
    common_asv_pressure_control_strategy_factory,
    individual_asv_rate_control_strategy_factory,
    individual_asv_pressure_control_strategy_factory,
    outlet_pressure_solver_factory,
    pure_methane_fluid_model,
):
    def create_process_solver_system(chart_data: ChartData, cell: MatrixCell) -> ProcessSolverSystem:
        shaft = VariableSpeedShaft()
        compressor = compressor_factory(chart_data=chart_data)
        stage_units = stage_units_factory(
            compressor=compressor,
            shaft=shaft,
            temperature_kelvin=303.15,
            remove_liquid_after_cooling=True,
        )
        inlet_stream = stream_factory(
            standard_rate_m3_per_day=cell.region.rate_sm3_day,
            pressure_bara=cell.region.suction_pressure_bara,
            temperature_kelvin=303.15,
            fluid_model=pure_methane_fluid_model,
        )
        choke = None
        choke_handler = None

        if cell.mode in {
            SolverPathMode.INDIVIDUAL_ASV_RATE,
            SolverPathMode.INDIVIDUAL_ASV_PRESSURE,
        }:
            process_units, recirculation_loops = with_individual_asv(stage_units)
            runner = process_runner_factory(
                units=process_units,
                configuration_handlers=[shaft, *recirculation_loops],
            )
            anti_surge_strategy = individual_asv_anti_surge_strategy_factory(
                runner=runner,
                recirculation_loop_ids=[loop.get_id() for loop in recirculation_loops],
                compressors=[compressor],
            )
            pressure_control_strategy = (
                individual_asv_rate_control_strategy_factory(
                    runner=runner,
                    recirculation_loop_ids=[loop.get_id() for loop in recirculation_loops],
                    compressors=[compressor],
                )
                if cell.mode is SolverPathMode.INDIVIDUAL_ASV_RATE
                else individual_asv_pressure_control_strategy_factory(
                    runner=runner,
                    recirculation_loop_ids=[loop.get_id() for loop in recirculation_loops],
                    compressors=[compressor],
                )
            )
        else:
            extra_before: list[ProcessUnit] = []
            extra_after: list[ProcessUnit] = []
            configuration_handlers = []
            if cell.mode in {SolverPathMode.DOWNSTREAM_CHOKE, SolverPathMode.UPSTREAM_CHOKE}:
                choke = choke_factory()
                choke_handler = choke_configuration_handler_factory(choke=choke)
                configuration_handlers.append(choke_handler)
                if cell.mode is SolverPathMode.UPSTREAM_CHOKE:
                    extra_before.append(choke)
                else:
                    extra_after.append(choke)

            runner, anti_surge_strategy, recirculation_loops, process_units = _build_common_asv_units(
                stage_units=stage_units,
                compressor=compressor,
                shaft=shaft,
                with_common_asv=with_common_asv,
                process_runner_factory=process_runner_factory,
                common_asv_anti_surge_strategy_factory=common_asv_anti_surge_strategy_factory,
                configuration_handlers=configuration_handlers,
                extra_units_before=extra_before,
                extra_units_after=extra_after,
            )
            process_pipeline = process_pipeline_factory(units=process_units)
            if cell.mode is SolverPathMode.NONE:
                pressure_control_strategy = NoPressureControlStrategy(
                    runner=runner,
                    process_pipeline_id=process_pipeline.get_id(),
                )
            elif cell.mode is SolverPathMode.DOWNSTREAM_CHOKE:
                assert choke_handler is not None
                pressure_control_strategy = downstream_choke_pressure_control_strategy_factory(
                    runner=runner,
                    choke_id=choke_handler.get_id(),
                )
            elif cell.mode is SolverPathMode.UPSTREAM_CHOKE:
                assert choke_handler is not None
                pressure_control_strategy = upstream_choke_pressure_control_strategy_factory(
                    runner=runner,
                    choke_id=choke_handler.get_id(),
                )
            else:
                first_loop = recirculation_loops[0]
                pressure_control_strategy = common_asv_pressure_control_strategy_factory(
                    runner=runner,
                    recirculation_loop_id=first_loop.get_id(),
                    first_compressor=compressor,
                )

        if cell.mode in {
            SolverPathMode.INDIVIDUAL_ASV_RATE,
            SolverPathMode.INDIVIDUAL_ASV_PRESSURE,
        }:
            process_pipeline = process_pipeline_factory(units=process_units)

        solver = outlet_pressure_solver_factory(
            shaft=shaft,
            runner=runner,
            anti_surge_strategy=anti_surge_strategy,
            pressure_control_strategy=pressure_control_strategy,
            process_pipeline_id=process_pipeline.get_id(),
        )
        return ProcessSolverSystem(
            solver=solver,
            runner=runner,
            inlet_stream=inlet_stream,
            shaft=shaft,
            recirculation_loops=tuple(recirculation_loops),
            choke=choke,
        )

    return create_process_solver_system


def _process_observation(system: ProcessSolverSystem, cell: MatrixCell) -> MatrixObservation:
    solution = system.solver.find_solution(
        pressure_constraint=FloatConstraint(cell.region.discharge_pressure_bara, abs_tol=PRESSURE_TOLERANCE),
        inlet_stream=system.inlet_stream,
    )
    failure_status = _status_from_process_solution(solution)
    recirculation_rates = tuple(
        configuration.value.recirculation_rate
        for configuration in solution.configuration
        if isinstance(configuration.value, RecirculationConfiguration)
    )
    speed = next(
        (
            configuration.value.speed
            for configuration in solution.configuration
            if isinstance(configuration.value, SpeedConfiguration)
        ),
        system.shaft.get_speed(),
    )
    choke_delta_pressure = next(
        (
            configuration.value.delta_pressure
            for configuration in solution.configuration
            if isinstance(configuration.value, ChokeConfiguration)
        ),
        None,
    )
    anti_surge_solution = system.solver.get_anti_surge_solution()
    anti_surge_recirculation_rates = tuple(
        configuration.value.recirculation_rate for configuration in anti_surge_solution.configuration
    )

    system.runner.apply_configurations(solution.configuration)
    try:
        outlet_pressure = system.runner.run(inlet_stream=system.inlet_stream).pressure_bara
    except RateTooHighError:
        outlet_pressure = np.nan

    return MatrixObservation(
        is_valid=solution.success,
        failure_status=failure_status,
        outlet_pressure_bara=outlet_pressure,
        speed=speed,
        power_mw=None,
        chart_area_flag=None,
        recirculation_rates=recirculation_rates,
        anti_surge_recirculation_rates=anti_surge_recirculation_rates,
        choke_delta_pressure=choke_delta_pressure,
        suction_pressure_after_upstream_choke_bara=None,
    )


def _assert_pressure_expectation(observation: MatrixObservation, cell: MatrixCell) -> None:
    expected_pressure = cell.region.discharge_pressure_bara
    expectation = cell.expectation.pressure_expectation
    if expectation is PressureExpectation.TARGET:
        assert observation.outlet_pressure_bara == pytest.approx(expected_pressure, abs=PRESSURE_TOLERANCE)
    elif expectation is PressureExpectation.ABOVE_TARGET:
        assert observation.outlet_pressure_bara > expected_pressure
    elif expectation is PressureExpectation.BELOW_TARGET:
        assert observation.outlet_pressure_bara < expected_pressure
    elif expectation is PressureExpectation.NAN:
        assert isnan(observation.outlet_pressure_bara)
    elif expectation is PressureExpectation.NOT_ASSERTED:
        return
    else:
        raise AssertionError(f"Unexpected pressure expectation: {expectation}")


def _assert_speed_boundary(observation: MatrixObservation, chart_data: ChartData, cell: MatrixCell) -> None:
    boundary_class = cell.region.speed_boundary_class
    if boundary_class is SpeedBoundaryClass.NOT_ASSERTED:
        return

    speeds = [curve.speed for curve in chart_data.get_adjusted_curves()]
    minimum_speed = min(speeds)
    maximum_speed = max(speeds)
    if boundary_class is SpeedBoundaryClass.MINIMUM:
        assert observation.speed == pytest.approx(minimum_speed, rel=1e-4)
    elif boundary_class is SpeedBoundaryClass.MAXIMUM:
        assert observation.speed == pytest.approx(maximum_speed, rel=1e-4)
    elif boundary_class is SpeedBoundaryClass.INTERNAL:
        assert minimum_speed < observation.speed < maximum_speed
    else:
        raise AssertionError(f"Unexpected speed boundary class: {boundary_class}")


def _assert_common_behavior(observation: MatrixObservation, chart_data: ChartData, cell: MatrixCell) -> None:
    assert observation.is_valid is cell.expectation.success
    assert observation.failure_status is cell.expectation.failure_status
    _assert_pressure_expectation(observation=observation, cell=cell)
    _assert_speed_boundary(observation=observation, chart_data=chart_data, cell=cell)


def _assert_control_behavior(observation: MatrixObservation, cell: MatrixCell) -> None:
    if cell.region.expect_auto_anti_surge:
        assert observation.has_anti_surge_recirculation
    elif cell.region.id in {"R1", "R6", "R7", "R8", "R9"} and cell.mode in {
        SolverPathMode.NONE,
        SolverPathMode.DOWNSTREAM_CHOKE,
        SolverPathMode.UPSTREAM_CHOKE,
    }:
        assert not observation.has_anti_surge_recirculation

    if cell.expectation.expect_pressure_control_recirculation:
        assert observation.has_recirculation

    if cell.expectation.expect_downstream_choke:
        assert observation.choke_delta_pressure is None or observation.choke_delta_pressure > 0.0
    elif cell.expectation.expect_upstream_choke:
        assert observation.choke_delta_pressure is None or observation.choke_delta_pressure > 0.0
    elif observation.choke_delta_pressure is not None:
        assert observation.choke_delta_pressure == pytest.approx(0.0, abs=PRESSURE_TOLERANCE)

    if cell.expectation.expect_upstream_choke and observation.suction_pressure_after_upstream_choke_bara is not None:
        assert observation.suction_pressure_after_upstream_choke_bara < cell.region.suction_pressure_bara


@pytest.mark.parametrize("cell", MATRIX_CELLS, ids=lambda cell: cell.id)
def test_legacy_solver_path_matrix(
    cell: MatrixCell,
    variable_speed_compressor_chart_data,
    legacy_train_factory,
):
    train = legacy_train_factory(
        chart_data=variable_speed_compressor_chart_data,
        pressure_control=PRESSURE_CONTROL_BY_MODE[cell.mode],
    )

    observation = _legacy_observation(train=train, cell=cell)

    _assert_common_behavior(observation=observation, chart_data=variable_speed_compressor_chart_data, cell=cell)
    assert observation.power_mw == pytest.approx(cell.expectation.power_mw, abs=POWER_TOLERANCE)
    expected_chart_area = _expected_legacy_chart_area(cell)
    if expected_chart_area is not None:
        assert observation.chart_area_flag is expected_chart_area
    _assert_control_behavior(observation=observation, cell=cell)


def _expected_legacy_chart_area(cell: MatrixCell) -> ChartAreaFlag | None:
    if cell.region.id == "R9" and cell.mode in {
        SolverPathMode.UPSTREAM_CHOKE,
        SolverPathMode.COMMON_ASV,
    }:
        return ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE
    return cell.region.expected_chart_area


@pytest.mark.parametrize("cell", PROCESS_MATRIX_PARAMS)
def test_process_solver_path_matrix(
    cell: MatrixCell,
    variable_speed_compressor_chart_data,
    process_solver_system_factory,
):
    system = process_solver_system_factory(chart_data=variable_speed_compressor_chart_data, cell=cell)

    observation = _process_observation(system=system, cell=cell)

    _assert_common_behavior(observation=observation, chart_data=variable_speed_compressor_chart_data, cell=cell)
    _assert_control_behavior(observation=observation, cell=cell)
