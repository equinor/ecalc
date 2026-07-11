"""v3 case factory for the single-stage solver-path matrix.

Reuses the existing matrix case definitions, assertion helpers and golden snapshot
from ``tests.libecalc.process.process_solver.compressor_solver_path_matrix`` — only
the system/constraint construction is v3-specific.
"""

from __future__ import annotations

import pandas as pd
import pytest

from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.process_concept_draft_v3.solver import Constraint

# Re-export the matrix vocabulary so the test module imports from one place.
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.single_stage_solver_path_matrix.assertions import (  # noqa: E501
    POWER_TOLERANCE,
    assert_pressure_expectation,
    assert_speed_boundary,
)
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.single_stage_solver_path_matrix.cases import (
    TEST_CASES,
    ExpectedOutcome,
    TrialCase,
)
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.two_stage_solver_path_matrix.assertions import (  # noqa: E501
    PRESSURE_TOLERANCE as TWO_STAGE_PRESSURE_TOLERANCE,
)
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.two_stage_solver_path_matrix.cases import (
    TwoStageTrialCase,
)

from ..conftest import INLET_TEMPERATURE_KELVIN, V3System, build_v3_system, make_constraint

__all__ = [
    "POWER_TOLERANCE",
    "TEST_CASES",
    "ExpectedOutcome",
    "TrialCase",
    "assert_pressure_expectation",
    "assert_speed_boundary",
]

PRESSURE_TOLERANCE = 0.01  # bara, the matrix target tolerance


@pytest.fixture
def v3_case_factory(stream_factory, fluid_service, pure_methane_fluid_model):
    def create(chart_data: ChartData, case: TrialCase) -> tuple[V3System, Constraint, object]:
        built = build_v3_system(
            pressure_control=case.mode,
            charts=[chart_data],
            fluid_service=fluid_service,
            inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            remove_liquid=True,
        )
        constraint = make_constraint(
            built, case.mode, case.region.discharge_pressure_bara, target_tolerance=PRESSURE_TOLERANCE
        )
        inlet = stream_factory(
            standard_rate_m3_per_day=case.region.rate_sm3_day,
            pressure_bara=case.region.suction_pressure_bara,
            temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            fluid_model=pure_methane_fluid_model,
        )
        return built, constraint, inlet

    return create


@pytest.fixture
def hp_compressor_chart_data(chart_data_factory, chart_curve_factory) -> ChartData:
    """HP stage chart: same 7 RPMs as LP, ~55% rates, ~115% head.

    Identical to the fixture in the two-stage process solver tests.
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
def v3_two_stage_case_factory(stream_factory, fluid_service, pure_methane_fluid_model):
    """Build a two-stage v3 system (LP + HP) with inlet stream for a TwoStageTrialCase."""

    def create(
        lp_chart_data: ChartData,
        hp_chart_data: ChartData,
        case: TwoStageTrialCase,
    ) -> tuple[V3System, Constraint, object]:
        built = build_v3_system(
            pressure_control=case.mode,
            charts=[lp_chart_data, hp_chart_data],
            fluid_service=fluid_service,
            inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            remove_liquid=True,
        )
        constraint = make_constraint(
            built, case.mode, case.region.discharge_pressure_bara, target_tolerance=TWO_STAGE_PRESSURE_TOLERANCE
        )
        inlet = stream_factory(
            standard_rate_m3_per_day=case.region.rate_sm3_day,
            pressure_bara=case.region.suction_pressure_bara,
            temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            fluid_model=pure_methane_fluid_model,
        )
        return built, constraint, inlet

    return create
