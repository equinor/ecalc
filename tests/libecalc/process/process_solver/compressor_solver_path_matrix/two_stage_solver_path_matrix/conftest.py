"""Fixtures for two-stage solver-path matrix tests.

Provides an HP compressor chart (~55% flow, ~115% head vs LP) and factories
that build both legacy CompressorTrainCommonShaft trains and process-domain
solver systems with two stages (LP + HP) sharing a single variable-speed shaft.
"""

from __future__ import annotations

import pandas as pd
import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.shaft import VariableSpeedShaft
from tests.libecalc.process.helpers import ProcessSolverSystem, StageConfig

from ..conftest import INLET_TEMPERATURE_KELVIN
from .cases import TwoStageTrialCase


@pytest.fixture
def hp_compressor_chart_data(chart_data_factory, chart_curve_factory) -> ChartData:
    """HP stage chart: same 7 RPMs as LP, ~55% rates, ~115% head.

    The narrower flow range and higher head per stage create asymmetric
    behavior where the HP stage has a tighter operating envelope — exactly
    the scenario needed to test per-stage anti-surge independence.
    """
    df = pd.DataFrame(
        [
            [10767, 2229.2, 185546.8, 0.72],
            [10767, 2475.6, 181427.1, 0.73],
            [10767, 2749.5, 175381.9, 0.74],
            [10767, 3021.2, 165160.7, 0.74],
            [10767, 3300.6, 151780.5, 0.72],
            [10767, 3541.5, 135073.3, 0.70],
            [11533, 2380.4, 213016.8, 0.72],
            [11533, 2749.5, 205717.8, 0.74],
            [11533, 3028.3, 197786.2, 0.74],
            [11533, 3315.4, 186031.0, 0.74],
            [11533, 3578.9, 169638.8, 0.72],
            [11533, 3799.4, 153642.3, 0.70],
            [10984, 2276.5, 192675.6, 0.72],
            [10984, 2751.1, 183605.6, 0.74],
            [10984, 3021.7, 174061.7, 0.74],
            [10984, 3304.9, 160896.5, 0.73],
            [10984, 3608.0, 139698.6, 0.70],
            [10435, 2160.4, 174129.6, 0.72],
            [10435, 2478.9, 169031.5, 0.74],
            [10435, 2751.1, 161888.9, 0.74],
            [10435, 3024.5, 150731.7, 0.74],
            [10435, 3436.9, 126160.8, 0.70],
            [9886, 2039.9, 156192.2, 0.72],
            [9886, 2476.1, 148723.8, 0.74],
            [9886, 2746.7, 140172.4, 0.74],
            [9886, 3029.4, 127209.6, 0.73],
            [9886, 3258.2, 113424.2, 0.70],
            [8787, 1818.3, 123543.4, 0.72],
            [8787, 2200.0, 117248.3, 0.74],
            [8787, 2474.5, 109509.4, 0.74],
            [8787, 2748.4, 96953.2, 0.72],
            [8787, 2883.1, 89969.9, 0.70],
            [7689, 1595.0, 94911.2, 0.72],
            [7689, 1927.2, 90211.8, 0.74],
            [7689, 2201.7, 83076.9, 0.74],
            [7689, 2527.3, 69121.7, 0.70],
        ],
        columns=["speed", "rate", "head", "efficiency"],
    )
    chart_curves = [
        chart_curve_factory(
            polytropic_head_joule_per_kg=data["head"].tolist(),
            rate_actual_m3_hour=data["rate"].tolist(),
            efficiency_fraction=data["efficiency"].tolist(),
            speed_rpm=float(speed),
        )
        for speed, data in df.groupby("speed")
    ]
    return chart_data_factory.from_curves(curves=chart_curves)


@pytest.fixture
def two_stage_legacy_train_factory(
    compressor_stage_factory,
    fluid_service,
    pure_methane_fluid_model,
):
    """Build a two-stage legacy CompressorTrainCommonShaft (LP + HP)."""

    def create(
        lp_chart_data: ChartData,
        hp_chart_data: ChartData,
        pressure_control: FixedSpeedPressureControl | None,
    ) -> CompressorTrainCommonShaft:
        shaft = VariableSpeedShaft()
        lp_stage: CompressorTrainStage = compressor_stage_factory(
            shaft=shaft,
            compressor_chart_data=lp_chart_data,
            inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            remove_liquid_after_cooling=True,
            pressure_drop_ahead_of_stage=0.0,
        )
        hp_stage: CompressorTrainStage = compressor_stage_factory(
            shaft=shaft,
            compressor_chart_data=hp_chart_data,
            inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            remove_liquid_after_cooling=True,
            pressure_drop_ahead_of_stage=0.0,
        )
        train = CompressorTrainCommonShaft(
            shaft=shaft,
            fluid_service=fluid_service,
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1,
            stages=[lp_stage, hp_stage],
            pressure_control=pressure_control,
            calculate_max_rate=False,
        )
        train._fluid_model = [pure_methane_fluid_model]
        return train

    return create


@pytest.fixture
def two_stage_process_case_factory(
    stream_factory,
    build_solver_system,
    pure_methane_fluid_model,
):
    """Build a two-stage process solver system (LP + HP) with inlet stream."""

    def create(
        lp_chart_data: ChartData,
        hp_chart_data: ChartData,
        case: TwoStageTrialCase,
    ) -> tuple[ProcessSolverSystem, FluidStream]:
        lp_config = StageConfig(
            chart_data=lp_chart_data,
            inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            remove_liquid_after_cooling=True,
        )
        hp_config = StageConfig(
            chart_data=hp_chart_data,
            inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            remove_liquid_after_cooling=True,
        )
        system = build_solver_system(
            stages=[lp_config, hp_config],
            pressure_control_type=case.mode,
        )
        inlet_stream = stream_factory(
            standard_rate_m3_per_day=case.region.rate_sm3_day,
            pressure_bara=case.region.suction_pressure_bara,
            temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            fluid_model=pure_methane_fluid_model,
        )
        return system, inlet_stream

    return create
