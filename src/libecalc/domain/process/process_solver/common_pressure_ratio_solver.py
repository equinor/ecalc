from collections.abc import Sequence
from typing import Final

from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.process_units.pressure_ratio_compressor import PressureRatioCompressor
from libecalc.domain.process.process_solver.configuration import Configuration
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.process_system_solver import ProcessSystemSolver
from libecalc.domain.process.process_solver.solver import (
    Solution,
    SolverFailureStatus,
    TargetNotAchievableEvent,
)
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class CommonPressureRatioSolver(ProcessSystemSolver):
    """Common pressure ratio solver for a SerialProcessSystem.

    No shaft speed — the total pressure ratio is distributed equally across the
    compressor stages (geometric mean). Each compressor stage applies the minimum
    recirculation required to stay above the surge line (individual anti-surge).

    TemperatureSetter and LiquidRemover are applied as deterministic pass-throughs
    and do not produce configuration entries.

    Note: despite the "Solver" name, there is no search or iteration here. The
    pressure ratio and surge floor are both computed analytically. The class exists
    to fulfill the find_solution(pressure_constraint, inlet_stream) -> Solution
    interface expected by FeasibilitySolver in parallel/stream-distribution settings.
    """

    def __init__(
        self,
        system: ProcessSystem,
        fluid_service: FluidService,
    ) -> None:
        for unit in system.get_process_units():
            if isinstance(unit, Compressor):
                raise DomainValidationException(
                    "CommonPressureRatioSolver cannot contain speed-based Compressor units. "
                    "Use CommonSpeedWithPressureControlSolver instead."
                )
        self._system: Final = system
        self._fluid_service: Final = fluid_service

    def find_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]:
        """Solve the system at the target outlet pressure using individual anti-surge.

        The total pressure ratio is split equally across compressor stages. Each
        compressor stage is evaluated at that ratio, with recirculation set to the
        minimum required to stay above the surge line.
        """
        process_units = self._system.get_process_units()
        compressors = [u for u in process_units if isinstance(u, PressureRatioCompressor)]
        n = len(compressors)
        assert n > 0, "SerialProcessSystem has no PressureRatioCompressor units."
        total_ratio = pressure_constraint.value / inlet_stream.pressure_bara
        if total_ratio <= 0:
            return Solution(
                success=False,
                configuration=[],
                failure_event=TargetNotAchievableEvent(
                    status=SolverFailureStatus.MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET,
                    achievable_value=inlet_stream.pressure_bara,
                    target_value=pressure_constraint.value,
                    source_id=self._system.get_id(),
                ),
            )

        pressure_ratio_per_stage = total_ratio ** (1.0 / n)

        configurations: list[Configuration[RecirculationConfiguration]] = []
        current_inlet = inlet_stream

        for unit in process_units:
            if isinstance(unit, PressureRatioCompressor):
                recirc_range = unit.get_recirculation_range_at_pressure_ratio(
                    inlet_stream=current_inlet,
                    pressure_ratio=pressure_ratio_per_stage,
                )
                # Individual anti-surge: apply minimum recirculation to stay above surge line.
                recirculation_rate = recirc_range.min

                configurations.append(
                    Configuration(
                        simulation_unit_id=unit.get_id(),
                        value=RecirculationConfiguration(recirculation_rate=recirculation_rate),
                    )
                )

                if recirculation_rate > 0.0:
                    inner_inlet = self._fluid_service.create_stream_from_standard_rate(
                        fluid_model=current_inlet.fluid_model,
                        pressure_bara=current_inlet.pressure_bara,
                        temperature_kelvin=current_inlet.temperature_kelvin,
                        standard_rate_m3_per_day=current_inlet.standard_rate_sm3_per_day + recirculation_rate,
                    )
                else:
                    inner_inlet = current_inlet

                outlet_with_recirc = unit.propagate_stream_at_pressure_ratio(
                    inner_inlet, pressure_ratio=pressure_ratio_per_stage
                )

                if recirculation_rate > 0.0:
                    current_inlet = self._fluid_service.create_stream_from_standard_rate(
                        fluid_model=outlet_with_recirc.fluid_model,
                        pressure_bara=outlet_with_recirc.pressure_bara,
                        temperature_kelvin=outlet_with_recirc.temperature_kelvin,
                        standard_rate_m3_per_day=outlet_with_recirc.standard_rate_sm3_per_day - recirculation_rate,
                    )
                else:
                    current_inlet = outlet_with_recirc
            else:
                # TemperatureSetter or LiquidRemover — deterministic pass-through, no configuration entry
                current_inlet = unit.propagate_stream(current_inlet)

        outlet_pressure = current_inlet.pressure_bara
        success = pressure_constraint == outlet_pressure

        if not success:
            if outlet_pressure < pressure_constraint.value:
                status = SolverFailureStatus.MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET
            else:
                status = SolverFailureStatus.MINIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_ABOVE_TARGET
            return Solution(
                success=False,
                configuration=configurations,
                failure_event=TargetNotAchievableEvent(
                    status=status,
                    achievable_value=outlet_pressure,
                    target_value=pressure_constraint.value,
                    source_id=self._system.get_id(),
                ),
            )

        return Solution(success=True, configuration=configurations)

    def get_max_standard_rate(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> float:
        """Maximum inlet standard rate [sm³/day] for which the system can meet target pressure.

        Iterates through stages at the common pressure ratio and finds the
        bottleneck — the stage with the lowest stonewall limit. Returns the
        corresponding maximum inlet standard rate.
        """
        process_units = self._system.get_process_units()
        compressors = [u for u in process_units if isinstance(u, PressureRatioCompressor)]
        n = len(compressors)
        if n == 0:
            return 0.0

        total_ratio = pressure_constraint.value / inlet_stream.pressure_bara
        if total_ratio <= 0:
            return 0.0

        pressure_ratio_per_stage = total_ratio ** (1.0 / n)

        max_inlet_rate = float("inf")
        current_inlet = inlet_stream

        for unit in process_units:
            if isinstance(unit, PressureRatioCompressor):
                recirc_range = unit.get_recirculation_range_at_pressure_ratio(
                    inlet_stream=current_inlet,
                    pressure_ratio=pressure_ratio_per_stage,
                )
                stage_max = current_inlet.standard_rate_sm3_per_day + recirc_range.max
                max_inlet_rate = min(max_inlet_rate, stage_max)

                current_inlet = unit.propagate_stream_at_pressure_ratio(
                    current_inlet, pressure_ratio=pressure_ratio_per_stage
                )
            else:
                current_inlet = unit.propagate_stream(current_inlet)

        return max(0.0, max_inlet_rate)
