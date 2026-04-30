from collections.abc import Sequence

import pytest

from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.configuration import ConfigurationHandlerId
from libecalc.process.process_solver.multi_pressure_solver import MultiPressureSolver
from libecalc.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.process.process_solver.pressure_control.downstream_choke import (
    DownstreamChokePressureControlStrategy,
)
from libecalc.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.pressure_control.upstream_choke import UpstreamChokePressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.shaft import Shaft


@pytest.fixture
def with_common_asv(recirculation_loop_factory, direct_mixer_factory, direct_splitter_factory):
    """Factory fixture: wrap all units in a single RecirculationLoop.

    Returns the loop, its ID, and the first compressor found in units.
    """

    def create(units: list[ProcessUnit]) -> tuple[RecirculationLoop, Sequence[ProcessUnit]]:
        mixer = direct_mixer_factory()
        splitter = direct_splitter_factory()
        loop = recirculation_loop_factory(mixer=mixer, splitter=splitter)
        return loop, [mixer, *units, splitter]

    return create


@pytest.fixture
def with_individual_asv(with_common_asv):
    """Factory fixture: wrap each Compressor in its own RecirculationLoop.

    Non-compressor units (e.g. TemperatureSetter) are kept in-place outside the loop.
    Returns the transformed unit list, the loop (configuration handler) list, and the compressor references.
    """

    def create(
        units: list[ProcessUnit],
    ) -> tuple[list[ProcessUnit], list[RecirculationLoop]]:
        process_units, loops = [], []
        for unit in units:
            if isinstance(unit, Compressor):
                recirculation_loop, loop_process_units = with_common_asv([unit])
                process_units.extend(loop_process_units)
                loops.append(recirculation_loop)
            else:
                process_units.append(unit)
        return process_units, loops

    return create


@pytest.fixture
def outlet_pressure_solver_factory(root_finding_strategy):
    def create_outlet_pressure_solver(
        shaft: Shaft,
        runner: ProcessRunner,
        anti_surge_strategy: AntiSurgeStrategy,
        pressure_control_strategy: PressureControlStrategy,
        process_pipeline_id: ProcessPipelineId,
    ):
        return OutletPressureSolver(
            shaft_id=shaft.get_id(),
            process_pipeline_id=process_pipeline_id,
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
        recirculation_loop_id: ConfigurationHandlerId,
        first_compressor: Compressor,
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
        recirculation_loop_ids: list[ConfigurationHandlerId],
        compressors: list[Compressor],
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
        recirculation_loop_id: ConfigurationHandlerId,
        first_compressor: Compressor,
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
        recirculation_loop_ids: list[ConfigurationHandlerId],
        compressors: list[Compressor],
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
        recirculation_loop_ids: list[ConfigurationHandlerId],
        compressors: list[Compressor],
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
            choke_configuration_handler_id=choke_id,
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
            choke_configuration_handler_id=choke_id,
        )

    return create


@pytest.fixture
def multi_pressure_solver_factory():
    def create_multi_pressure_solver(
        segments: list[OutletPressureSolver],
    ) -> MultiPressureSolver:
        return MultiPressureSolver(segments=segments)

    return create_multi_pressure_solver


@pytest.fixture
def variable_speed_chart_data_factory():
    def create_variable_speed_chart_data(chart_data_factory, *, min_rate, max_rate, head_hi, head_lo, eff):
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

    return create_variable_speed_chart_data
