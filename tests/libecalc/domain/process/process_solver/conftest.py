import pytest

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.multi_pressure_solver import MultiPressureSolver
from libecalc.domain.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.domain.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.domain.process.process_solver.pressure_control.downstream_choke import (
    DownstreamChokePressureControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.pressure_control.upstream_choke import UpstreamChokePressureControlStrategy
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.process_system.process_system import ProcessSystemId, create_process_system_id
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.chart import ChartCurve


@pytest.fixture
def with_individual_asv(recirculation_loop_factory, process_system_factory):
    """Factory fixture: wrap each Compressor in its own RecirculationLoop.

    Non-compressor units (e.g. TemperatureSetter) are kept in-place outside the loop.
    Returns the transformed unit list, the loop IDs, and the compressor references.
    """

    def create(units: list[ProcessUnit]) -> tuple[list[ProcessUnit], list[ProcessSystemId], list[Compressor]]:
        result, loop_ids, compressors = [], [], []
        for unit in units:
            if isinstance(unit, Compressor):
                loop = recirculation_loop_factory(inner_process=process_system_factory([unit]))
                result.append(loop)
                loop_ids.append(loop.get_id())
                compressors.append(unit)
            else:
                result.append(unit)
        return result, loop_ids, compressors

    return create


@pytest.fixture
def with_common_asv(recirculation_loop_factory, process_system_factory):
    """Factory fixture: wrap all units in a single RecirculationLoop.

    Returns the loop, its ID, and the first compressor found in units.
    """

    def create(units: list[ProcessUnit]) -> tuple[ProcessUnit, ProcessSystemId, Compressor]:
        loop = recirculation_loop_factory(inner_process=process_system_factory(units))
        first_compressor = next(u for u in units if isinstance(u, Compressor))
        return loop, loop.get_id(), first_compressor

    return create


@pytest.fixture
def outlet_pressure_solver_factory(root_finding_strategy):
    def create_outlet_pressure_solver(
        shaft: Shaft,
        runner: ProcessRunner,
        anti_surge_strategy: AntiSurgeStrategy,
        pressure_control_strategy: PressureControlStrategy,
        process_system_id: ProcessSystemId | None = None,
    ):
        return OutletPressureSolver(
            shaft_id=shaft.get_id(),
            process_system_id=process_system_id or create_process_system_id(),
            runner=runner,
            anti_surge_strategy=anti_surge_strategy,
            pressure_control_strategy=pressure_control_strategy,
            root_finding_strategy=root_finding_strategy,
            speed_boundary=shaft.get_speed_boundary(),
        )

    return create_outlet_pressure_solver


@pytest.fixture
def common_asv_anti_surge_strategy_factory(root_finding_strategy):
    def create(
        runner: ProcessRunner,
        recirculation_loop_id: ProcessSystemId,
        first_compressor: ProcessUnit,
    ) -> CommonASVAntiSurgeStrategy:
        return CommonASVAntiSurgeStrategy(
            simulator=runner,
            recirculation_loop_id=recirculation_loop_id,
            first_compressor=first_compressor,
            root_finding_strategy=root_finding_strategy,
        )

    return create


@pytest.fixture
def individual_asv_anti_surge_strategy_factory():
    def create(
        runner: ProcessRunner,
        recirculation_loop_ids: list[ProcessSystemId],
        compressors: list[ProcessUnit],
    ) -> IndividualASVAntiSurgeStrategy:
        return IndividualASVAntiSurgeStrategy(
            recirculation_loop_ids=recirculation_loop_ids,
            compressors=compressors,
            simulator=runner,
        )

    return create


@pytest.fixture
def common_asv_pressure_control_strategy_factory(root_finding_strategy):
    def create(
        runner: ProcessRunner,
        recirculation_loop_id: ProcessSystemId,
        first_compressor: ProcessUnit,
    ) -> CommonASVPressureControlStrategy:
        return CommonASVPressureControlStrategy(
            simulator=runner,
            recirculation_loop_id=recirculation_loop_id,
            first_compressor=first_compressor,
            root_finding_strategy=root_finding_strategy,
        )

    return create


@pytest.fixture
def individual_asv_rate_control_strategy_factory():
    def create(
        runner: ProcessRunner,
        recirculation_loop_ids: list[ProcessSystemId],
        compressors: list[ProcessUnit],
    ) -> IndividualASVRateControlStrategy:
        return IndividualASVRateControlStrategy(
            simulator=runner,
            recirculation_loop_ids=recirculation_loop_ids,
            compressors=compressors,
        )

    return create


@pytest.fixture
def individual_asv_pressure_control_strategy_factory(root_finding_strategy):
    def create(
        runner: ProcessRunner,
        recirculation_loop_ids: list[ProcessSystemId],
        compressors: list[ProcessUnit],
    ) -> IndividualASVPressureControlStrategy:
        return IndividualASVPressureControlStrategy(
            simulator=runner,
            recirculation_loop_ids=recirculation_loop_ids,
            compressors=compressors,
            root_finding_strategy=root_finding_strategy,
        )

    return create


@pytest.fixture
def upstream_choke_pressure_control_strategy_factory(root_finding_strategy):
    def create(
        runner: ProcessRunner,
        choke_id: ProcessUnitId,
    ) -> UpstreamChokePressureControlStrategy:
        return UpstreamChokePressureControlStrategy(
            simulator=runner,
            choke_id=choke_id,
            root_finding_strategy=root_finding_strategy,
        )

    return create


@pytest.fixture
def downstream_choke_pressure_control_strategy_factory():
    def create(
        runner: ProcessRunner,
        choke_id: ProcessUnitId,
    ) -> DownstreamChokePressureControlStrategy:
        return DownstreamChokePressureControlStrategy(
            simulator=runner,
            choke_id=choke_id,
        )

    return create


@pytest.fixture
def multi_pressure_solver_factory():
    def create_multi_pressure_solver(
        segments: list[OutletPressureSolver],
    ) -> MultiPressureSolver:
        return MultiPressureSolver(segments=segments)

    return create_multi_pressure_solver


def make_variable_speed_chart_data(chart_data_factory, *, min_rate, max_rate, head_hi, head_lo, eff):
    return chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=75.0,
                rate_actual_m3_hour=[min_rate, max_rate],
                polytropic_head_joule_per_kg=[head_hi, head_lo],
                efficiency_fraction=[eff, eff],
            ),
            ChartCurve(
                speed_rpm=105.0,
                rate_actual_m3_hour=[min_rate, max_rate],
                polytropic_head_joule_per_kg=[head_hi * 1.05, head_lo * 1.05],
                efficiency_fraction=[eff, eff],
            ),
        ],
        control_margin=0.0,
    )
