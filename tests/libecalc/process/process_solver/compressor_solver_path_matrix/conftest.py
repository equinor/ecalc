"""Fixtures for solver-path matrix tests."""

from __future__ import annotations

import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.shaft import VariableSpeedShaft
from tests.libecalc.process.helpers import ProcessSolverSystem

from .cases import TrialCase

INLET_TEMPERATURE_KELVIN = 303.15


@pytest.fixture(scope="session")
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
            inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN,
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
