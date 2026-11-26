"""The pump that the pump tests share.

With ``DENSITY_KG_PER_M3``, 100 J/kg of head is 1 bar: the head is 90 to 60 bar at 2000 rpm and 175 to 130 bar
at 3000 rpm. A single-speed pump has the 2000 rpm curve. At 600 m3/h the head is 80 bar at 2000 rpm and
170 bar at 3000 rpm, so 125 bar is 2500 rpm.
"""

from libecalc.process.chart import ChartCurve
from libecalc.process.chart.chart import ChartData
from libecalc.testing.chart_data_factory import ChartDataFactory

DENSITY_KG_PER_M3 = 1000.0

MINIMUM_SPEED_CURVE = ChartCurve(
    speed_rpm=2000.0,
    rate_actual_m3_hour=[200.0, 400.0, 600.0, 800.0, 1000.0],
    polytropic_head_joule_per_kg=[9000.0, 8500.0, 8000.0, 7000.0, 6000.0],
    efficiency_fraction=[0.5, 0.7, 0.8, 0.75, 0.7],
)
MAXIMUM_SPEED_CURVE = ChartCurve(
    speed_rpm=3000.0,
    rate_actual_m3_hour=[300.0, 600.0, 800.0, 1000.0, 1200.0],
    polytropic_head_joule_per_kg=[17500.0, 17000.0, 16000.0, 15000.0, 13000.0],
    efficiency_fraction=[0.5, 0.8, 0.8, 0.75, 0.7],
)


def single_speed_pump_chart() -> ChartData:
    return ChartDataFactory.from_curves(curves=[MINIMUM_SPEED_CURVE])


def variable_speed_pump_chart() -> ChartData:
    return ChartDataFactory.from_curves(curves=[MINIMUM_SPEED_CURVE, MAXIMUM_SPEED_CURVE])
