from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import get_args

import pytest

from libecalc.ecalc_model.process_simulation import PressureControlType
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import RecirculationConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.shaft import VariableSpeedShaft
from tests.libecalc.process.helpers import ProcessSolverBuilder, ProcessSolverSystem, StageConfig

PRESSURE_CONTROL_TYPES = get_args(PressureControlType)


@dataclass(frozen=True)
class SolverRunResult:
    success: bool
    speed: float
    outlet_pressure_bara: float
    recirculation_rates: tuple[float, ...]
    power_mw: float


@pytest.fixture
def two_stage_configs(chart_data_factory) -> list[StageConfig]:
    return [
        StageConfig(
            chart_data=chart_data_factory.from_design_point(rate=1200, head=70_000, efficiency=0.75),
            inlet_temperature_kelvin=300.0,
        ),
        StageConfig(
            chart_data=chart_data_factory.from_design_point(rate=900, head=50_000, efficiency=0.72),
            inlet_temperature_kelvin=300.0,
        ),
    ]


@pytest.fixture
def inlet_stream(stream_factory) -> FluidStream:
    return stream_factory(standard_rate_m3_per_day=500_000.0, pressure_bara=30.0, temperature_kelvin=300.0)


def _run_solver(system: ProcessSolverSystem, inlet_stream: FluidStream) -> SolverRunResult:
    target_pressure = FloatConstraint(75.0, abs_tol=1e-3)
    solution = system.solver.find_solution(pressure_constraint=target_pressure, inlet_stream=inlet_stream)
    system.runner.apply_configurations(solution.configuration)
    outlet_stream = system.runner.run(inlet_stream=inlet_stream)
    speed = solution.get_configuration(system.shaft.get_id()).speed
    recirculation_rates = tuple(
        configuration.value.recirculation_rate
        for configuration in solution.configuration
        if isinstance(configuration.value, RecirculationConfiguration)
    )
    return SolverRunResult(
        success=solution.success,
        speed=speed,
        outlet_pressure_bara=outlet_stream.pressure_bara,
        recirculation_rates=recirculation_rates,
        power_mw=sum(compressor.power_megawatt for compressor in system.compressors),
    )


@pytest.mark.parametrize("pressure_control_type", PRESSURE_CONTROL_TYPES)
def test_builder_produces_working_solver_for_each_production_pressure_control_mode(
    pressure_control_type,
    fluid_service,
    two_stage_configs,
    inlet_stream,
):
    system = ProcessSolverBuilder(
        stages=two_stage_configs,
        pressure_control_type=pressure_control_type,
        fluid_service=fluid_service,
    ).build()

    result = _run_solver(system=system, inlet_stream=inlet_stream)

    assert result.success
    assert result.outlet_pressure_bara == pytest.approx(75.0, abs=1e-3)
    assert result.power_mw > 0.0


@pytest.mark.parametrize("pressure_control_type", ["COMMON_ASV", "INDIVIDUAL_ASV_PRESSURE"])
def test_builder_matches_hand_assembled_solver_for_complex_modes(
    pressure_control_type,
    fluid_service,
    two_stage_configs,
    inlet_stream,
    manually_build_solver_system,
):
    builder_system = ProcessSolverBuilder(
        stages=two_stage_configs,
        pressure_control_type=pressure_control_type,
        fluid_service=fluid_service,
    ).build()
    manual_system = manually_build_solver_system(
        stages=two_stage_configs,
        pressure_control_type=pressure_control_type,
    )

    builder_result = _run_solver(system=builder_system, inlet_stream=inlet_stream)
    manual_result = _run_solver(system=manual_system, inlet_stream=inlet_stream)

    assert builder_result.success is manual_result.success
    assert builder_result.speed == pytest.approx(manual_result.speed, rel=1e-6)
    assert builder_result.outlet_pressure_bara == pytest.approx(manual_result.outlet_pressure_bara, abs=1e-6)
    assert builder_result.recirculation_rates == pytest.approx(manual_result.recirculation_rates, rel=1e-6)
    assert builder_result.power_mw == pytest.approx(manual_result.power_mw, rel=1e-6)


def test_builder_supports_multi_stage_individual_asv(
    fluid_service,
    two_stage_configs,
    inlet_stream,
):
    system = ProcessSolverBuilder(
        stages=two_stage_configs,
        pressure_control_type="INDIVIDUAL_ASV_RATE",
        fluid_service=fluid_service,
    ).build()

    result = _run_solver(system=system, inlet_stream=inlet_stream)

    assert len(system.compressors) == 2
    assert len(system.recirculation_loops) == 2
    assert result.success


@pytest.fixture
def manually_build_solver_system(
    compressor_factory,
    stage_units_factory,
    with_common_asv,
    with_individual_asv,
    process_pipeline_factory,
    process_runner_factory,
    common_asv_anti_surge_strategy_factory,
    individual_asv_anti_surge_strategy_factory,
    common_asv_pressure_control_strategy_factory,
    individual_asv_pressure_control_strategy_factory,
    outlet_pressure_solver_factory,
):
    def create(
        *,
        stages: Sequence[StageConfig],
        pressure_control_type: str,
    ) -> ProcessSolverSystem:
        shaft = VariableSpeedShaft()
        compressors = tuple(compressor_factory(chart_data=stage.chart_data) for stage in stages)
        stage_unit_groups = [
            stage_units_factory(
                compressor=compressor,
                shaft=shaft,
                temperature_kelvin=stage.inlet_temperature_kelvin,
                pressure_drop_ahead_of_stage=stage.pressure_drop_ahead_of_stage,
                remove_liquid_after_cooling=stage.remove_liquid_after_cooling,
            )
            for stage, compressor in zip(stages, compressors, strict=True)
        ]

        if pressure_control_type == "COMMON_ASV":
            recirculation_loop, process_units = with_common_asv(
                [unit for stage_units in stage_unit_groups for unit in stage_units]
            )
            recirculation_loops = (recirculation_loop,)
            runner = process_runner_factory(units=process_units, configuration_handlers=[shaft, recirculation_loop])
            anti_surge_strategy = common_asv_anti_surge_strategy_factory(
                runner=runner,
                recirculation_loop_id=recirculation_loop.get_id(),
                first_compressor=compressors[0],
            )
            pressure_control_strategy = common_asv_pressure_control_strategy_factory(
                runner=runner,
                recirculation_loop_id=recirculation_loop.get_id(),
                first_compressor=compressors[0],
            )
        elif pressure_control_type == "INDIVIDUAL_ASV_PRESSURE":
            process_units, recirculation_loops = with_individual_asv(
                [unit for stage_units in stage_unit_groups for unit in stage_units]
            )
            recirculation_loops = tuple(recirculation_loops)
            recirculation_loop_ids = [loop.get_id() for loop in recirculation_loops]
            runner = process_runner_factory(units=process_units, configuration_handlers=[shaft, *recirculation_loops])
            anti_surge_strategy = individual_asv_anti_surge_strategy_factory(
                runner=runner,
                recirculation_loop_ids=recirculation_loop_ids,
                compressors=list(compressors),
            )
            pressure_control_strategy = individual_asv_pressure_control_strategy_factory(
                runner=runner,
                recirculation_loop_ids=recirculation_loop_ids,
                compressors=list(compressors),
            )
        else:
            raise ValueError(f"Unsupported manual assembly mode: {pressure_control_type}")

        pipeline = process_pipeline_factory(units=process_units)
        solver = outlet_pressure_solver_factory(
            shaft=shaft,
            runner=runner,
            anti_surge_strategy=anti_surge_strategy,
            pressure_control_strategy=pressure_control_strategy,
            process_pipeline_id=pipeline.get_id(),
        )
        return ProcessSolverSystem(
            solver=solver,
            runner=runner,
            pipeline=pipeline,
            shaft=shaft,
            compressors=compressors,
            recirculation_loops=recirculation_loops,
            choke=None,
        )

    return create
