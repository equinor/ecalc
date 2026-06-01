from __future__ import annotations

from dataclasses import dataclass
from typing import get_args

import pytest

from libecalc.ecalc_model.process_simulation import PressureControlType
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_unit import ProcessUnit
from libecalc.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.configuration import RecirculationConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.process.process_solver.pressure_control.downstream_choke import DownstreamChokePressureControlStrategy
from libecalc.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.process.process_solver.pressure_control.upstream_choke import UpstreamChokePressureControlStrategy
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.liquid_remover import LiquidRemover
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from tests.libecalc.process.helpers import ProcessSolverBuilder, ProcessSolverSystem, StageConfig

PRESSURE_CONTROL_TYPES = get_args(PressureControlType)
PRESSURE_CONTROL_STRATEGY_TYPES = {
    "DOWNSTREAM_CHOKE": DownstreamChokePressureControlStrategy,
    "UPSTREAM_CHOKE": UpstreamChokePressureControlStrategy,
    "COMMON_ASV": CommonASVPressureControlStrategy,
    "INDIVIDUAL_ASV_RATE": IndividualASVRateControlStrategy,
    "INDIVIDUAL_ASV_PRESSURE": IndividualASVPressureControlStrategy,
}


@dataclass(frozen=True)
class SolverRunResult:
    success: bool
    speed: float
    outlet_pressure_bara: float
    recirculation_rates: tuple[float, ...]


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


@pytest.mark.parametrize("pressure_control_type", PRESSURE_CONTROL_TYPES)
def test_builder_wires_expected_solver_strategies(
    pressure_control_type,
    fluid_service,
    two_stage_configs,
):
    system = ProcessSolverBuilder(
        stages=two_stage_configs,
        pressure_control_type=pressure_control_type,
        fluid_service=fluid_service,
    ).build()
    expected_anti_surge_strategy_type = (
        CommonASVAntiSurgeStrategy if pressure_control_type == "COMMON_ASV" else IndividualASVAntiSurgeStrategy
    )

    assert isinstance(system.solver.runner.anti_surge_strategy, expected_anti_surge_strategy_type)
    assert isinstance(system.solver.pressure_control_strategy, PRESSURE_CONTROL_STRATEGY_TYPES[pressure_control_type])


def test_builder_uses_single_recirculation_loop_for_common_asv(
    fluid_service,
    two_stage_configs,
):
    system = ProcessSolverBuilder(
        stages=two_stage_configs,
        pressure_control_type="COMMON_ASV",
        fluid_service=fluid_service,
    ).build()

    assert len(system.compressors) == 2
    assert len(system.recirculation_loops) == 1
    assert system.choke is None
    assert _unit_types(system.pipeline.get_process_units()) == (
        DirectMixer,
        TemperatureSetter,
        Choke,
        LiquidRemover,
        Compressor,
        TemperatureSetter,
        Choke,
        LiquidRemover,
        Compressor,
        DirectSplitter,
    )


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
    assert system.choke is None
    assert _unit_types(system.pipeline.get_process_units()) == (
        DirectMixer,
        TemperatureSetter,
        Choke,
        LiquidRemover,
        Compressor,
        DirectSplitter,
        DirectMixer,
        TemperatureSetter,
        Choke,
        LiquidRemover,
        Compressor,
        DirectSplitter,
    )
    assert result.success


@pytest.mark.parametrize(
    ("pressure_control_type", "expected_choke_index"),
    [
        ("UPSTREAM_CHOKE", 0),
        ("DOWNSTREAM_CHOKE", -1),
    ],
)
def test_builder_places_pressure_control_choke_around_individual_asv_topology(
    pressure_control_type,
    expected_choke_index,
    fluid_service,
    two_stage_configs,
):
    system = ProcessSolverBuilder(
        stages=two_stage_configs,
        pressure_control_type=pressure_control_type,
        fluid_service=fluid_service,
    ).build()

    process_units = system.pipeline.get_process_units()

    assert len(system.compressors) == 2
    assert len(system.recirculation_loops) == 2
    assert system.choke is not None
    assert process_units[expected_choke_index] is system.choke


def _unit_types(process_units: list[ProcessUnit]) -> tuple[type[ProcessUnit], ...]:
    return tuple(type(unit) for unit in process_units)
