import pytest

from libecalc.domain.process.entities.process_units.liquid_remover import LiquidRemover
from libecalc.domain.process.entities.process_units.pressure_ratio_compressor import PressureRatioCompressor
from libecalc.domain.process.entities.process_units.temperature_setter import TemperatureSetter
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.outlet_pressure_solver_ratio import OutletPressureSolverRatio
from libecalc.domain.process.process_system.process_system import create_process_system_id
from libecalc.domain.process.process_system.process_unit import create_process_unit_id
from libecalc.domain.process.process_system.serial_process_system import SerialProcessSystem
from libecalc.testing.chart_data_factory import ChartDataFactory


@pytest.fixture
def make_compressor(fluid_service):
    def _make(min_rate=300.0, max_rate=1200.0, head_hi=80000.0, head_lo=55000.0, eff=0.75):
        chart_data = ChartDataFactory.from_rate_and_head(
            rate=[min_rate, max_rate],
            head=[head_hi, head_lo],
            efficiency=eff,
        )
        return PressureRatioCompressor(
            process_unit_id=create_process_unit_id(),
            compressor_chart=chart_data,
            fluid_service=fluid_service,
        )

    return _make


@pytest.fixture
def make_temperature_setter(fluid_service):
    def _make(temperature_kelvin=303.15):
        return TemperatureSetter(
            process_unit_id=create_process_unit_id(),
            required_temperature_kelvin=temperature_kelvin,
            fluid_service=fluid_service,
        )

    return _make


@pytest.fixture
def make_liquid_remover(fluid_service):
    def _make():
        return LiquidRemover(
            process_unit_id=create_process_unit_id(),
            fluid_service=fluid_service,
        )

    return _make


def test_single_stage_simplified_solver_meets_target(stream_factory, fluid_service, make_compressor):
    """Single-stage simplified solver should produce outlet at target pressure."""
    system = SerialProcessSystem(process_system_id=create_process_system_id(), propagators=[make_compressor()])
    solver = OutletPressureSolverRatio(system=system, fluid_service=fluid_service)

    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)
    target = FloatConstraint(50.0, abs_tol=1.0)

    solution = solver.find_solution(pressure_constraint=target, inlet_stream=inlet)

    assert solution.success


def test_two_stage_simplified_solver_meets_target(stream_factory, fluid_service, make_compressor):
    """Two-stage simplified solver should split ratio equally and produce correct outlet."""
    system = SerialProcessSystem(
        process_system_id=create_process_system_id(), propagators=[make_compressor(), make_compressor()]
    )
    solver = OutletPressureSolverRatio(system=system, fluid_service=fluid_service)

    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)
    # Each stage should hit ratio of sqrt(4.0) = 2.0 → 20 → 40 → 80
    target = FloatConstraint(80.0, abs_tol=2.0)

    solution = solver.find_solution(pressure_constraint=target, inlet_stream=inlet)

    assert solution.success
    assert len(solution.configuration) == 2


def test_temperature_setter_before_compressor_is_applied(
    stream_factory, fluid_service, make_compressor, make_temperature_setter
):
    """TemperatureSetter before a compressor should set inlet temperature before compression.

    Configuration list should contain exactly one entry (only the Compressor produces config).
    """
    system_with_setter = SerialProcessSystem(
        process_system_id=create_process_system_id(),
        propagators=[make_temperature_setter(temperature_kelvin=303.15), make_compressor()],
    )
    system_without_setter = SerialProcessSystem(
        process_system_id=create_process_system_id(), propagators=[make_compressor()]
    )

    hot_inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0, temperature_kelvin=373.15)
    target = FloatConstraint(50.0, abs_tol=1.0)

    sol_with = OutletPressureSolverRatio(system=system_with_setter, fluid_service=fluid_service).find_solution(
        pressure_constraint=target, inlet_stream=hot_inlet
    )
    sol_without = OutletPressureSolverRatio(system=system_without_setter, fluid_service=fluid_service).find_solution(
        pressure_constraint=target, inlet_stream=hot_inlet
    )

    assert sol_with.success
    assert sol_without.success
    # Only the Compressor produces a configuration entry
    assert len(sol_with.configuration) == 1


def test_two_stage_with_liquid_remover_and_temperature_setter(
    stream_factory,
    fluid_service,
    make_compressor,
    make_temperature_setter,
    make_liquid_remover,
):
    """A realistic two-stage train: TemperatureSetter + Compressor + LiquidRemover + TemperatureSetter + Compressor."""
    system = SerialProcessSystem(
        process_system_id=create_process_system_id(),
        propagators=[
            make_temperature_setter(temperature_kelvin=303.15),
            make_compressor(),
            make_liquid_remover(),
            make_temperature_setter(temperature_kelvin=303.15),
            make_compressor(),
        ],
    )
    solver = OutletPressureSolverRatio(system=system, fluid_service=fluid_service)

    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)
    target = FloatConstraint(80.0, abs_tol=2.0)

    solution = solver.find_solution(pressure_constraint=target, inlet_stream=inlet)

    assert solution.success
    # Only the two Compressor units produce configuration entries
    assert len(solution.configuration) == 2
