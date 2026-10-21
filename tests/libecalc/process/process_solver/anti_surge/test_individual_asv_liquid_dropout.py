"""Individual ASV with a rich gas that drops liquid in the stage scrubber.

Recirculation is sized at the compressor inlet, so it must enter the stage after the
LiquidRemover. If it is mixed in upstream, the scrubber removes part of it and the
compressor ends up below the surge line.
"""

import pytest

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import RecirculationConfiguration
from libecalc.process.process_solver.float_constraint import AbsoluteTolerance, FloatConstraint
from tests.libecalc.process.helpers import StageConfig

INLET_PRESSURE_BARA = 50.0
# 20 °C at 50 bara: the ultra rich gas condenses roughly 11 wt% in the scrubber.
SCRUBBER_TEMPERATURE_KELVIN = 293.15
# Low enough that every stage needs recirculation to stay above surge.
INLET_STANDARD_RATE_SM3_PER_DAY = 200_000.0


@pytest.fixture
def ultra_rich_inlet_stream(stream_factory, fluid_model_ultra_rich) -> FluidStream:
    return stream_factory(
        standard_rate_m3_per_day=INLET_STANDARD_RATE_SM3_PER_DAY,
        pressure_bara=INLET_PRESSURE_BARA,
        temperature_kelvin=SCRUBBER_TEMPERATURE_KELVIN,
        fluid_model=fluid_model_ultra_rich,
    )


@pytest.fixture
def stage_factory(chart_data_factory):
    def create(number_of_stages: int) -> list[StageConfig]:
        return [
            StageConfig(
                chart_data=chart_data_factory.from_design_point(rate=1200, head=50_000, efficiency=0.75),
                inlet_temperature_kelvin=SCRUBBER_TEMPERATURE_KELVIN,
                remove_liquid_after_cooling=True,
            )
            for _ in range(number_of_stages)
        ]

    return create


@pytest.mark.parametrize(
    ("number_of_stages", "target_pressure_bara"),
    [(1, 70.0), (2, 90.0)],
)
def test_individual_asv_keeps_compressors_above_surge_when_scrubber_removes_liquid(
    number_of_stages,
    target_pressure_bara,
    build_solver_system,
    stage_factory,
    ultra_rich_inlet_stream,
):
    system = build_solver_system(stages=stage_factory(number_of_stages), pressure_control_type="DOWNSTREAM_CHOKE")
    target_pressure = FloatConstraint(target_pressure_bara, AbsoluteTolerance(1e-3))

    solution = system.solver.find_solution(pressure_targets=[target_pressure], inlet_stream=ultra_rich_inlet_stream)

    assert solution.success, solution.failure

    # Preconditions: liquid is removed and every stage recirculates, so the scenario exercises the bug.
    system.runner.apply_configurations(solution.configuration)
    outlet_stream = system.runner.run(inlet_stream=ultra_rich_inlet_stream)
    assert outlet_stream.mass_rate_kg_per_h < ultra_rich_inlet_stream.mass_rate_kg_per_h
    recirculation_rates = [
        configuration.value.recirculation_rate
        for configuration in solution.configuration
        if isinstance(configuration.value, RecirculationConfiguration)
    ]
    assert len(recirculation_rates) == number_of_stages
    assert all(rate > 0.0 for rate in recirculation_rates)


def test_individual_asv_recirculation_loop_is_mass_neutral_when_scrubber_removes_liquid(
    build_solver_system,
    stage_factory,
    ultra_rich_inlet_stream,
):
    # Whatever is recirculated is taken out again by the splitter, so the outlet mass rate
    # must not depend on the recirculation rate.
    system = build_solver_system(stages=stage_factory(1), pressure_control_type="DOWNSTREAM_CHOKE")
    compressor = system.compressors[0]
    loop = system.recirculation_loops[0]
    system.shaft.set_speed(compressor.compressor_chart.maximum_speed)

    compressor_inlet_stream = system.runner.run(inlet_stream=ultra_rich_inlet_stream, to_id=compressor.get_id())
    within_capacity = compressor.get_recirculation_range(inlet_stream=compressor_inlet_stream)
    span = within_capacity.max - within_capacity.min
    outlet_mass_rates = []
    for recirculation_rate in (within_capacity.min + 0.25 * span, within_capacity.min + 0.75 * span):
        loop.set_recirculation_rate(recirculation_rate)
        outlet_mass_rates.append(system.runner.run(inlet_stream=ultra_rich_inlet_stream).mass_rate_kg_per_h)

    assert outlet_mass_rates[0] == pytest.approx(outlet_mass_rates[1], rel=1e-9)
    assert outlet_mass_rates[0] < ultra_rich_inlet_stream.mass_rate_kg_per_h
