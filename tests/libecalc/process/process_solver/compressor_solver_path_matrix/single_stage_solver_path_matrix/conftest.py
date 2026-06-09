"""Fixtures for single-stage solver-path matrix tests."""

from __future__ import annotations

import pytest

from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from tests.libecalc.process.helpers import ProcessSolverSystem

from ..conftest import INLET_TEMPERATURE_KELVIN
from .cases import TrialCase


@pytest.fixture
def process_solver_case_factory(stream_factory, build_solver_system, pure_methane_fluid_model):
    def create(chart_data: ChartData, case: TrialCase) -> tuple[ProcessSolverSystem, FluidStream]:
        system = build_solver_system(
            chart_data=chart_data,
            pressure_control_type=case.mode,
            inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            remove_liquid_after_cooling=True,
        )
        inlet_stream = stream_factory(
            standard_rate_m3_per_day=case.region.rate_sm3_day,
            pressure_bara=case.region.suction_pressure_bara,
            temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            fluid_model=pure_methane_fluid_model,
        )
        return system, inlet_stream

    return create
