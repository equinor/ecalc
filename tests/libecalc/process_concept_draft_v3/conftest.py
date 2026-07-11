"""Shared fixtures and builders for the process_concept_draft_v3 suite.

Root fixtures (``fluid_service``, ``stream_factory``, the session NeqSim
service) are inherited from ``tests/conftest.py`` automatically — never start
NeqsimService manually here. The builders below mirror the chart/stream numbers
the existing solver tests use so parity assertions stay trivial.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop as LegacyRecirculationLoop
from libecalc.process.process_solver.solver_assembly import ProcessSolverSystem, assemble_solver
from libecalc.process.process_units.choke import Choke as ChokeKernel
from libecalc.process.process_units.compressor import Compressor as CompressorKernel
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from libecalc.process.shaft import VariableSpeedShaft
from libecalc.process_concept_draft_v3 import (
    Choke,
    CommonASVLoop,
    CompressorStage,
    Shaft,
    chain,
)
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import (
    FROM_CAPACITY,
    FROM_CHART,
    INF,
    Bounds,
    Constraint,
    CoupledParameter,
    DistributionRule,
    Probe,
    Target,
)
from libecalc.testing.chart_data_factory import ChartDataFactory

INLET_TEMPERATURE_KELVIN = 303.15

MEDIUM_COMPOSITION = FluidComposition(
    nitrogen=0.74373,
    CO2=2.415619,
    methane=85.60145,
    ethane=6.707826,
    propane=2.611471,
    i_butane=0.45077,
    n_butane=0.691702,
    i_pentane=0.210714,
    n_pentane=0.197937,
    n_hexane=0.368786,
)


@pytest.fixture(scope="session")
def medium_fluid_model() -> FluidModel:
    return FluidModel(composition=MEDIUM_COMPOSITION, eos_model=EoSModel.SRK)


@pytest.fixture
def make_stream(fluid_service: FluidService, medium_fluid_model: FluidModel):
    def _make(
        standard_rate_sm3_per_day: float,
        pressure_bara: float,
        temperature_kelvin: float = 288.15,
    ) -> FluidStream:
        return fluid_service.create_stream_from_standard_rate(
            fluid_model=medium_fluid_model,
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
            standard_rate_m3_per_day=standard_rate_sm3_per_day,
        )

    return _make


def make_variable_speed_chart(
    min_rate: float = 500.0,
    max_rate: float = 1500.0,
    head_hi: float = 70_000.0,
    head_lo: float = 50_000.0,
    efficiency: float = 0.75,
) -> ChartData:
    """Five affinity-law-scaled speed curves (60-100 rpm), as in the solver fixtures."""
    curves = []
    for speed in [60.0, 70.0, 80.0, 90.0, 100.0]:
        f = speed / 100.0
        curves.append(
            ChartCurve(
                speed_rpm=speed,
                rate_actual_m3_hour=[min_rate * f, max_rate * f],
                polytropic_head_joule_per_kg=[head_hi * f**2, head_lo * f**2],
                efficiency_fraction=[efficiency, efficiency],
            )
        )
    return ChartDataFactory.from_curves(curves, control_margin=0.0)


@pytest.fixture
def variable_speed_chart() -> ChartData:
    return make_variable_speed_chart()


# --------------------------------------------------------------------- v3 builders


@dataclass
class V3System:
    system: object
    shaft: Shaft
    stages: list[CompressorStage]
    loop: CommonASVLoop | None
    choke: Choke | None
    target_unit: object


def build_v3_system(
    pressure_control: str,
    charts: list[ChartData],
    fluid_service: FluidService,
    inlet_temperature_kelvin: float = INLET_TEMPERATURE_KELVIN,
    remove_liquid: bool = False,
) -> V3System:
    """Mirror of the legacy ProcessSolverBuilder: per-stage cooler, optional liquid removal.

    COMMON_ASV wraps the stages in one CommonASVLoop; the choke modes prepend/
    append a Choke; per-stage recirculation is the stage's own (auto) parameter.
    """
    shaft = Shaft()
    stages = [
        CompressorStage(
            chart=chart, shaft=shaft, inlet_temperature_kelvin=inlet_temperature_kelvin, remove_liquid=remove_liquid
        )
        for chart in charts
    ]
    loop: CommonASVLoop | None = None
    choke: Choke | None = None

    if pressure_control == "COMMON_ASV":
        loop = CommonASVLoop()
        units = [loop.inlet, *stages, loop.outlet]
        target_unit: object = stages[-1]
    elif pressure_control == "DOWNSTREAM_CHOKE":
        choke = Choke()
        units = [*stages, choke]
        target_unit = choke
    elif pressure_control == "UPSTREAM_CHOKE":
        choke = Choke()
        units = [choke, *stages]
        target_unit = stages[-1]
    else:  # INDIVIDUAL_ASV_* — stages with their own recirculation (constraint built in task 05)
        units = list(stages)
        target_unit = stages[-1]

    system = chain("feed", *units, fluid_service=fluid_service)
    return V3System(system, shaft, stages, loop, choke, target_unit)


def make_constraint(
    built: V3System, pressure_control: str, target_pressure: float, target_tolerance: float = 1e-3
) -> Constraint:
    target = Target(probe=Probe.outlet_pressure(built.target_unit), value=target_pressure, tolerance=target_tolerance)
    fallback: Constraint | None
    if pressure_control == "COMMON_ASV":
        fallback = Constraint(vary=Param(built.loop, "rate_sm3_per_day"), target=target, bounds=FROM_CAPACITY)
    elif pressure_control in {"DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE"}:
        fallback = Constraint(vary=Param(built.choke, "delta_pressure"), target=target, bounds=Bounds(0.0, INF))
    elif pressure_control in {"INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE"}:
        rule = (
            DistributionRule.BALANCED_RATE
            if pressure_control == "INDIVIDUAL_ASV_RATE"
            else DistributionRule.BALANCED_PRESSURE
        )
        coupled = CoupledParameter(
            name=pressure_control.lower(),
            params=tuple(Param(stage, "recirculation_rate") for stage in built.stages),
            rule=rule,
        )
        fallback = Constraint(vary=coupled, target=target, bounds=Bounds(0.0, 1.0))
    else:
        fallback = None
    return Constraint(vary=Param(built.shaft, "speed"), target=target, bounds=FROM_CHART, fallback=fallback)


# --------------------------------------------------------------------- legacy parity builder


def build_legacy_system(
    stage_charts: list[ChartData],
    pressure_control_type: str,
    service: FluidService,
    inlet_temperature_kelvin: float = INLET_TEMPERATURE_KELVIN,
) -> ProcessSolverSystem:
    """Legacy solver wiring matching the v3 topology (per stage [cooler, compressor], ASV loops)."""
    shaft = VariableSpeedShaft()
    compressors: list[CompressorKernel] = []
    stage_units = []
    for chart in stage_charts:
        compressor = CompressorKernel(compressor_chart=chart, fluid_service=service)
        shaft.connect(compressor)
        compressors.append(compressor)
        cooler = TemperatureSetter(required_temperature_kelvin=inlet_temperature_kelvin, fluid_service=service)
        stage_units.append([cooler, compressor])

    def wrap(units):
        mixer, splitter = DirectMixer(), DirectSplitter()
        return LegacyRecirculationLoop(mixer=mixer, splitter=splitter), [mixer, *units, splitter]

    if pressure_control_type == "COMMON_ASV":
        loop, process_units = wrap([unit for units in stage_units for unit in units])
        recirculation_loops = [loop]
    else:
        process_units, recirculation_loops = [], []
        for units in stage_units:
            loop, wrapped = wrap(units)
            recirculation_loops.append(loop)
            process_units.extend(wrapped)

    choke = None
    choke_handler = None
    configuration_handlers = [shaft, *recirculation_loops]
    if pressure_control_type in {"DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE"}:
        choke = ChokeKernel(fluid_service=service)
        choke_handler = ChokeConfigurationHandler(choke=choke)
        configuration_handlers.append(choke_handler)
        process_units = (
            [*process_units, choke] if pressure_control_type == "DOWNSTREAM_CHOKE" else [choke, *process_units]
        )

    return assemble_solver(
        process_units=process_units,
        configuration_handlers=configuration_handlers,
        compressors=compressors,
        recirculation_loops=recirculation_loops,
        shaft=shaft,
        pipeline_name="v3-parity-pipeline",
        pressure_control_type=pressure_control_type,  # type: ignore[arg-type]
        choke=choke,
        choke_configuration_handler=choke_handler,
    )
