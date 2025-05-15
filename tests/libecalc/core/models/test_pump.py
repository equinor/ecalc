import numpy as np
import pandas as pd
import pytest

from libecalc.common.serializable_chart import ChartCurveDTO, VariableSpeedChartDTO
from libecalc.domain.process.core.chart.chart import SingleSpeedChart, VariableSpeedChart, ChartCurve
from libecalc.domain.process.pump.pump import PumpSingleSpeed, PumpVariableSpeed
from libecalc.domain.process.pump.pump import _adjust_for_head_margin


def test_adjust_for_head_margin():
    heads = np.asarray([2, 3, 4, 5, 6, 3, 4, 5, 6, 7])
    maximum_heads = np.asarray([3, 3, 3, 3, 3, 4, 4, 4, 4, 4])
    head_margin = 2

    heads_adjusted = _adjust_for_head_margin(heads=heads, maximum_heads=maximum_heads, head_margin=head_margin)

    expected = np.asarray([2, 3, 3, 3, 6, 3, 4, 4, 4, 7])

    np.testing.assert_allclose(heads_adjusted, expected)


@pytest.fixture
def single_speed_pump_chart():
    return SingleSpeedChart(
        rate_actual_m3_hour=[277, 524, 666, 832, 834, 927],
        polytropic_head_joule_per_kg=[10415.277000000002, 9845.316, 9254.754, 8308.089, 8312.994, 7605.693],
        efficiency_fraction=[0.4759, 0.6426, 0.6871, 0.7052, 0.7061, 0.6908],
        speed_rpm=1,
    )


def test_pump_single_speed(single_speed_pump_chart):
    pump = PumpSingleSpeed(pump_chart=single_speed_pump_chart)
    density = 1021  # kg/m3

    rate = np.asarray([0, 6648.0, 100000])
    suction_pressure = np.asarray([0.0, 1.0, 1000.0])
    discharge_pressure = np.asarray([1.0, 107.30993, 10000.0])
    fluid_density = np.asarray([density] * len(rate))

    result = pump.evaluate_rate_ps_pd_density(
        rate=rate,
        suction_pressures=suction_pressure,
        discharge_pressures=discharge_pressure,
        fluid_density=fluid_density,
    )

    np.testing.assert_allclose(result.energy_usage, [0, 1.719326, np.nan], rtol=0.001)
    np.testing.assert_allclose(result.suction_pressure, suction_pressure)
    np.testing.assert_allclose(result.discharge_pressure, discharge_pressure, rtol=0.001)


def test_pump_single_speed_above_maximum_head(single_speed_pump_chart):
    pump = PumpSingleSpeed(pump_chart=single_speed_pump_chart)

    # Head above maximum head
    assert np.isnan(
        pump.evaluate_rate_ps_pd_density(
            rate=np.asarray([6648.0]),
            suction_pressures=np.asarray([1.0]),
            discharge_pressures=np.asarray([108.0]),
            fluid_density=np.asarray([1021.0]),
        ).energy_usage[0]
    )

    pump_with_head_margin = PumpSingleSpeed(
        pump_chart=single_speed_pump_chart,
        head_margin=98.1,  # joule / kg
    )
    assert pump_with_head_margin.evaluate_rate_ps_pd_density(
        rate=np.asarray([6648.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([108.0]),
        fluid_density=np.asarray([1021.0]),
    ).energy_usage[0] == pytest.approx(1.7193256025478039)
    assert np.isnan(
        pump_with_head_margin.evaluate_rate_ps_pd_density(
            rate=np.asarray([6648.0]),
            suction_pressures=np.asarray([1.0]),
            discharge_pressures=np.asarray([109.0]),
            fluid_density=np.asarray([1021.0]),
        ).energy_usage[0]
    )


def test_single_speed_pump_adjustent_factors(single_speed_pump_chart):
    pump = PumpSingleSpeed(pump_chart=single_speed_pump_chart)
    density = 1021  # kg/m3

    rate = np.asarray([6648.0])
    suction_pressure = np.asarray([1.0])
    discharge_pressure = np.asarray([107.30993])
    fluid_density = np.asarray([density])

    result = pump.evaluate_rate_ps_pd_density(
        rate=rate,
        suction_pressures=suction_pressure,
        discharge_pressures=discharge_pressure,
        fluid_density=fluid_density,
    ).energy_usage[0]
    assert result == pytest.approx(1.7193256)

    # With adjustment
    constant = 10
    factor = 1.2

    pump_adjusted = PumpSingleSpeed(
        pump_chart=single_speed_pump_chart,
        energy_usage_adjustment_constant=constant,
        energy_usage_adjustment_factor=factor,
    )
    assert pump_adjusted.evaluate_rate_ps_pd_density(
        rate=rate,
        suction_pressures=suction_pressure,
        discharge_pressures=discharge_pressure,
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(constant + factor * result)

    # Rate equal to minimum rate in input curve, smaller head
    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([6648.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([100]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(1.7193256)

    # Recirc rate, allowed speed
    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([3000.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([100]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(1.7193256)

    # Intermediate rate, allowed speed
    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([14400.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([90]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(2.43325027)

    # Rate too large
    assert np.isnan(
        pump.evaluate_rate_ps_pd_density(
            rate=np.asarray([24000.0]),
            suction_pressures=np.asarray([1.0]),
            discharge_pressures=np.asarray([90]),
            fluid_density=fluid_density,
        ).energy_usage[0]
    )

    # Head too large
    assert np.isnan(
        pump.evaluate_rate_ps_pd_density(
            rate=np.asarray([14400.0]),
            suction_pressures=np.asarray([1.0]),
            discharge_pressures=np.asarray([101]),
            fluid_density=fluid_density,
        ).energy_usage[0]
    )


@pytest.fixture
def vsd_pump_test_variable_speed_chart_curves() -> VariableSpeedChart:
    df = pd.DataFrame(
        [
            [2650, 277, 1061.7, 0.4759],
            [2650, 524, 1003.6, 0.6426],
            [2650, 666, 943.4, 0.6871],
            [2650, 832, 846.9, 0.7052],
            [2650, 834, 847.4, 0.7061],
            [2650, 927, 775.3, 0.6908],
            [2900, 296, 1293, 0.47],
            [2900, 370, 1275, 0.52],
            [2900, 443, 1258, 0.57],
            [2900, 517, 1240, 0.62],
            [2900, 591, 1213, 0.65],
            [2900, 665, 1182, 0.68],
            [2900, 738, 1143, 0.69],
            [2900, 812, 1098, 0.70],
            [2900, 886, 1051, 0.71],
            [2900, 960, 996, 0.70],
            [3165, 316, 1538, 0.47],
            [3165, 392, 1520, 0.52],
            [3165, 467, 1501, 0.57],
            [3165, 542, 1483, 0.62],
            [3165, 617, 1455, 0.65],
            [3165, 693, 1423, 0.67],
            [3165, 768, 1382, 0.69],
            [3165, 843, 1334, 0.70],
            [3165, 919, 1284, 0.71],
            [3165, 994, 1231, 0.71],
            [3425, 336, 1778.7, 0.4717],
            [3425, 577, 1718.7, 0.6203],
            [3425, 708, 1665.2, 0.6683],
            [3425, 842, 1587.8, 0.6996],
            [3425, 824, 1601.9, 0.695],
            [3425, 826, 1601.9, 0.6975],
            [3425, 825, 1602.7, 0.6981],
            [3425, 1028, 1460.6, 0.7193],
        ],
        columns=["speed", "rate", "head", "efficiency"],
    )

    chart_curves = []
    for speed, data in df.groupby("speed"):
        chart_curve = ChartCurve(
            rate_actual_m3_hour=data["rate"].tolist(),
            polytropic_head_joule_per_kg=[x * 9.81 for x in data["head"].tolist()],  # meter liquid column to joule / kg
            efficiency_fraction=data["efficiency"].tolist(),
            speed_rpm=float(speed),
        )
        chart_curves.append(chart_curve)

    return VariableSpeedChart(curves=chart_curves)


def test_variable_speed_pump(vsd_pump_test_variable_speed_chart_curves):
    pump = PumpVariableSpeed(pump_chart=vsd_pump_test_variable_speed_chart_curves)

    density = 1021  # kg/m3

    rate = np.asarray([0, 6648.0, 100000])
    suction_pressure = np.asarray([0.0, 1.0, 1000.0])
    discharge_pressure = np.asarray([1.0, 107.30993, 10000.0])
    fluid_density = np.asarray([density] * len(rate))

    result = pump.evaluate_rate_ps_pd_density(
        rate=rate,
        suction_pressures=suction_pressure,
        discharge_pressures=discharge_pressure,
        fluid_density=fluid_density,
    )

    np.testing.assert_allclose(result.energy_usage, [0, 1.719326, np.nan], rtol=0.001)
    np.testing.assert_allclose(result.suction_pressure, suction_pressure)
    np.testing.assert_allclose(result.discharge_pressure, discharge_pressure, rtol=0.001)


def test_variable_speed_pump_pt2(vsd_pump_test_variable_speed_chart_curves, caplog):
    pump = PumpVariableSpeed(pump_chart=vsd_pump_test_variable_speed_chart_curves)

    # Along minimum speed line
    # pumpchar unit rate: 277, head: 1061.7
    rate = np.asarray([6648.0])
    suction_pressure = np.asarray([1.0])
    discharge_pressure = np.asarray([107.30993])
    fluid_density = np.asarray([1021])

    result = pump.evaluate_rate_ps_pd_density(
        rate=rate,
        suction_pressures=suction_pressure,
        discharge_pressures=discharge_pressure,
        fluid_density=fluid_density,
    ).energy_usage[0]
    assert result == pytest.approx(1.7193256025478039)

    np.testing.assert_allclose(
        pump.evaluate_rate_ps_pd_density(
            rate=np.asarray([6648.0]),
            suction_pressures=np.asarray([1.0]),
            discharge_pressures=np.asarray([107.30993]),
            fluid_density=np.asarray([1021]),
        ).energy_usage[0],
        1.7193256025478039,
        rtol=0.001,
    )
    assert np.isnan(
        pump.evaluate_rate_ps_pd_density(
            rate=np.asarray([6648.0]),
            suction_pressures=np.asarray([1.0]),
            discharge_pressures=np.asarray([180]),
            fluid_density=np.asarray([1021]),
        ).energy_usage[0]
    )

    pump_with_head_margin = PumpVariableSpeed(
        pump_chart=vsd_pump_test_variable_speed_chart_curves,
        head_margin=98.1,
    )
    np.testing.assert_allclose(
        pump_with_head_margin.evaluate_rate_ps_pd_density(
            rate=np.asarray([6648.0]),
            suction_pressures=np.asarray([1.0]),
            discharge_pressures=np.asarray([180]),  # give head = 1787.14, max is 1778.7, margin 10 ok
            fluid_density=np.asarray([1021]),
        ).energy_usage[0],
        3.5250749461946147,
        rtol=1e-3,
    )

    # With adjustment
    constant = 10
    factor = 1.2

    pump_adjusted = PumpVariableSpeed(
        pump_chart=vsd_pump_test_variable_speed_chart_curves,
        energy_usage_adjustment_constant=constant,
        energy_usage_adjustment_factor=factor,
    )
    assert pump_adjusted.evaluate_rate_ps_pd_density(
        rate=np.asarray([6648.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([107.30993]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(constant + factor * result)

    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([22248.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([78.654126]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(2.89460588)

    # Along maximum speed line
    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([8064.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([179.15476]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(3.52507465)

    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([24672.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([147.293842]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(5.80773243)

    # Points inside envelope
    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([15408.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([128.10]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(3.411238640)

    # Recirc rate
    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([7200.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([161]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(3.019016553)

    # Recirc rate, choke head
    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([2400.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([61]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(1.7193256)

    # Choke head below minimum speed line
    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([12576.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([61]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(2.27689743)

    # Choke head right of minimum speed line
    assert pump.evaluate_rate_ps_pd_density(
        rate=np.asarray([22800.0]),
        suction_pressures=np.asarray([1.0]),
        discharge_pressures=np.asarray([61]),
        fluid_density=fluid_density,
    ).energy_usage[0] == pytest.approx(3.52037671)

    # Rate too large - should give nan
    assert np.isnan(
        pump.evaluate_rate_ps_pd_density(
            rate=np.asarray([27600.0]),
            suction_pressures=np.asarray([1.0]),
            discharge_pressures=np.asarray([61.0]),
            fluid_density=fluid_density,
        ).energy_usage[0]
    )

    # Head too large - should give nan
    assert np.isnan(
        pump.evaluate_rate_ps_pd_density(
            rate=np.asarray([22800.0]),
            suction_pressures=np.asarray([1.0]),
            discharge_pressures=np.asarray([161.0]),
            fluid_density=fluid_density,
        ).energy_usage[0]
    )

    # Head too large - should give nan
    assert np.isnan(
        pump.evaluate_rate_ps_pd_density(
            rate=np.asarray([4800]),
            suction_pressures=np.asarray([1.0]),
            discharge_pressures=np.asarray([201]),
            fluid_density=fluid_density,
        ).energy_usage[0]
    )


def test_chart_curve_data(single_speed_pump_chart, caplog):
    rate_values = single_speed_pump_chart.rate_values
    head_values = single_speed_pump_chart.head_values
    efficiency_values = single_speed_pump_chart.efficiency_values

    chart_curve_data1 = SingleSpeedChart(
        rate_actual_m3_hour=list(rate_values),
        polytropic_head_joule_per_kg=list(head_values),
        efficiency_fraction=list(efficiency_values),
        speed_rpm=1,
    )
    np.testing.assert_allclose(chart_curve_data1.rate_values, rate_values)
    np.testing.assert_allclose(chart_curve_data1.head_values, head_values)
    np.testing.assert_allclose(
        chart_curve_data1.efficiency_values,
        efficiency_values,
    )
