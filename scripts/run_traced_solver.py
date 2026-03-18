"""Standalone script that sets up a 2-stage compressor train with common ASV,
runs the OutletPressureSolver with tracing enabled, and opens the event viewer GUI.

Usage:
    uv run python scripts/run_traced_solver.py
"""

from __future__ import annotations

from ecalc_neqsim_wrapper import NeqsimService
from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.process_units.rate_modifier.rate_modifier import RateModifier
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.process_units.temperature_setter import TemperatureSetter
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.event_service import EventService
from libecalc.domain.process.process_solver.event_viewer import show_events
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.domain.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.domain.process.process_solver.process_system_runner import ProcessSystemRunner
from libecalc.domain.process.process_solver.search_strategies import ScipyRootFindingStrategy
from libecalc.domain.process.process_solver.tracing_process_runner import TracingProcessRunner
from libecalc.domain.process.process_solver.tracing_process_unit import TracingProcessUnit
from libecalc.domain.process.process_system.process_system import create_process_system_id
from libecalc.domain.process.process_system.process_unit import create_process_unit_id
from libecalc.domain.process.process_system.serial_process_system import SerialProcessSystem
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.testing.chart_data_factory import ChartDataFactory


def main() -> None:
    # Initialize the NeqSim thermodynamic service (JVM bridge)
    with NeqsimService.factory(use_jpype=False).initialize():
        _run_solver()


def _run_solver() -> None:
    fluid_service = NeqSimFluidService.instance()

    # Fluid composition (medium gas ~19.4 kg/kmol)
    composition = FluidComposition(
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
    fluid_model = FluidModel(composition=composition, eos_model=EoSModel.SRK)

    # Shared variable-speed shaft
    shaft = VariableSpeedShaft()

    # Chart data for each stage (same design points as the test)
    chart_data_factory = ChartDataFactory()
    stage1_chart_data = chart_data_factory.from_design_point(rate=1200, head=70000, efficiency=0.75)
    stage2_chart_data = chart_data_factory.from_design_point(rate=900, head=50000, efficiency=0.72)

    temperature = 300  # kelvin

    # Build compressor train stages
    def make_compressor(chart_data):
        return Compressor(
            process_unit_id=create_process_unit_id(),
            compressor_chart=chart_data,
            fluid_service=fluid_service,
            shaft=shaft,
        )

    compressor1 = make_compressor(stage1_chart_data)
    compressor2 = make_compressor(stage2_chart_data)

    # Speed boundary = intersection of individual compressor speed ranges
    speed_boundaries = [compressor1.get_speed_boundary(), compressor2.get_speed_boundary()]
    speed_boundary = Boundary(
        min=max(b.min for b in speed_boundaries),
        max=min(b.max for b in speed_boundaries),
    )

    # ---- Tracing infrastructure ----
    event_service = EventService()

    # Wrap the compressor units with tracing so propagate_stream calls are recorded
    traced_compressor1 = TracingProcessUnit(compressor1, event_service)
    traced_compressor2 = TracingProcessUnit(compressor2, event_service)

    # Build the process system using traced compressors
    inner_system = SerialProcessSystem(
        process_system_id=create_process_system_id(),
        propagators=[traced_compressor1, traced_compressor2],
    )
    common_asv = RecirculationLoop(
        inner_process=inner_system,
        process_system_id=create_process_system_id(),
        fluid_service=fluid_service,
    )

    # Build the runner and wrap it with tracing
    inner_runner = ProcessSystemRunner(shaft=shaft, units=[common_asv])
    runner = TracingProcessRunner(inner_runner, event_service)

    # Root finding strategy
    root_finding_strategy = ScipyRootFindingStrategy()

    # Anti-surge and pressure control strategies
    # NOTE: strategies receive the unwrapped compressor1 so they can call
    #       CompressorStageProcessUnit methods (get_recirculation_range, etc.)
    anti_surge_strategy = CommonASVAntiSurgeStrategy(
        simulator=runner,
        recirculation_loop_id=common_asv.get_id(),
        first_compressor=compressor1,
        root_finding_strategy=root_finding_strategy,
    )
    pressure_control_strategy = CommonASVPressureControlStrategy(
        simulator=runner,
        recirculation_loop_id=common_asv.get_id(),
        first_compressor=compressor1,
        root_finding_strategy=root_finding_strategy,
    )

    # Build the solver
    solver = OutletPressureSolver(
        shaft=shaft,
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
        pressure_control_strategy=pressure_control_strategy,
        root_finding_strategy=root_finding_strategy,
        speed_boundary=speed_boundary,
    )

    # ---- Run the solve ----
    target_pressure = FloatConstraint(75)
    inlet_stream = fluid_service.create_stream_from_standard_rate(
        fluid_model=fluid_model,
        pressure_bara=30.0,
        temperature_kelvin=temperature,
        standard_rate_m3_per_day=500_000.0,
    )

    print(f"Inlet stream: P={inlet_stream.pressure_bara:.2f} bara, T={inlet_stream.temperature_kelvin:.1f} K")
    print(f"Target outlet pressure: {target_pressure.value} bara")
    print("Solving...")

    solution = solver.find_solution(
        pressure_constraint=target_pressure,
        inlet_stream=inlet_stream,
    )

    print(f"Solution found: success={solution.success}")
    for cfg in solution.configuration:
        print(f"  {type(cfg.value).__name__}: {cfg.value}")

    # Apply solution and run to verify
    runner.apply_configurations(solution.configuration)
    outlet_stream = runner.run(inlet_stream=inlet_stream)
    print(f"Outlet stream: P={outlet_stream.pressure_bara:.4f} bara")

    events = event_service.get_events()
    print(f"\nRecorded {len(events)} events. Launching viewer...")

    # Collect the flat list of process units for the diagram.
    # RecirculationLoop.get_process_units() returns: [mixer, compressor1, compressor2, splitter]
    # But our traced compressors replaced the originals in the serial system,
    # so get_process_units() will return [mixer, traced_compressor1, traced_compressor2, splitter].
    process_units = common_asv.get_process_units()

    show_events(event_service, process_units=process_units)


if __name__ == "__main__":
    main()
