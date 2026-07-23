"""Closed-form liquid pump process graph.

A pump process simulation is a fixed, serial liquid topology built around a single closed-form
``Pump``:

    inlet -> recirc mixer -> pump -> recirc splitter -> choke -> outlet
                  ^                        |
                  +--------- recycle ------+

It mirrors the compressor process-graph contract (typed units, connections, streams per
connection, a recirculation loop) so a consuming application can persist, reconstruct and
visualise it with a pattern analogous to the compressor - while staying liquid-typed and
solver-free. The mixer, splitter and choke are the faithful representation of minimum-flow
recirculation and downstream choking (identical in shape to a compressor anti-surge recycle and
downstream choke); their streams follow directly from the closed-form pump result, so there is no
iteration.
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from types import MappingProxyType
from typing import Final, NewType, Self
from uuid import UUID

from libecalc.common.ddd import value_object
from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.value_objects.chart.chart import Chart
from libecalc.process.process_pipeline.process_pipeline import (
    ProcessUnitConnection,
    ProcessUnitConnectionId,
)
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.pump import Pump, PumpEvaluationResult

PumpProcessSimulationId = NewType("PumpProcessSimulationId", UUID)
LiquidRecirculationLoopId = NewType("LiquidRecirculationLoopId", UUID)


class LiquidProcessUnitType(StrEnum):
    INLET = "INLET"
    DIRECT_MIXER = "DIRECT_MIXER"
    PUMP = "PUMP"
    DIRECT_SPLITTER = "DIRECT_SPLITTER"
    CHOKE = "CHOKE"
    OUTLET = "OUTLET"


class LiquidProcessUnit(Entity[ProcessUnitId]):
    """A typed node in the pump process graph, identified for persistence and visualisation."""

    def __init__(
        self,
        unit_type: LiquidProcessUnitType,
        name: str,
        id: ProcessUnitId | None = None,
    ):
        self._id: Final[ProcessUnitId] = id or LiquidProcessUnit._create_id()
        self._unit_type = unit_type
        self._name = name

    def get_id(self) -> ProcessUnitId:
        return self._id

    @property
    def unit_type(self) -> LiquidProcessUnitType:
        return self._unit_type

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessUnitId:
        return ProcessUnitId(ecalc_id_generator())


class LiquidRecirculationLoop(Entity[LiquidRecirculationLoopId]):
    """Minimum-flow recirculation routing recycle from the splitter back to the mixer.

    Mirrors the compressor recirculation-loop topology (``splitter_id`` + ``mixer_id``); like the
    gas recirculation loop it is its own concept with its own identity, not a serial connection.
    The recycle rate is not attributed to a node: it is a scalar on
    ``PumpEvaluationResult.recirculation_rate_m3_per_hour`` and is also implied by the connection
    streams (the operating-rate step between the ``inlet -> mixer`` and ``mixer -> pump`` edges).
    """

    def __init__(
        self,
        splitter_id: ProcessUnitId,
        mixer_id: ProcessUnitId,
        id: LiquidRecirculationLoopId | None = None,
    ):
        self._id: Final[LiquidRecirculationLoopId] = id or LiquidRecirculationLoop._create_id()
        self._splitter_id = splitter_id
        self._mixer_id = mixer_id

    def get_id(self) -> LiquidRecirculationLoopId:
        return self._id

    @property
    def splitter_id(self) -> ProcessUnitId:
        return self._splitter_id

    @property
    def mixer_id(self) -> ProcessUnitId:
        return self._mixer_id

    @classmethod
    def _create_id(cls: type[Self]) -> LiquidRecirculationLoopId:
        return LiquidRecirculationLoopId(ecalc_id_generator())


@value_object
class PumpOperatingInput:
    """The physical input for a single pump evaluation.

    ``inlet_stream`` always carries a physical inlet (positive pressure and density); its rate may
    be zero, which the pump treats as not running (zero power, outlet pressure equal to the inlet
    pressure). ``required_discharge_pressure_bara`` is the duty target; it is only meaningful while
    the pump runs. This domain is time-agnostic: any period/time mapping is kept by the caller.
    """

    inlet_stream: LiquidStream
    required_discharge_pressure_bara: float


@value_object
class PumpOperatingResult:
    """Result of one evaluation: the pump operating result plus the stream on every connection.

    An evaluation where the pump does not run (zero rate) still produces a result - zero power, the
    outlet pressure equal to the inlet pressure, and zero-flow streams on every connection.
    """

    pump_result: PumpEvaluationResult
    connection_streams: Mapping[ProcessUnitConnectionId, LiquidStream]


class PumpProcessSimulation(Entity[PumpProcessSimulationId]):
    """A closed-form pump process graph that evaluates itself period by period.

    The graph structure (units, connections, recirculation loop) is fixed and built once. Each
    period is evaluated by the closed-form ``Pump`` and projected onto the connection streams;
    there is no solver.

    Args:
        pump: The closed-form pump (encapsulates the chart, minimum flow and its id).
        name: Human-readable name; also the name of the pump unit.
        process_simulation_id: Identity of the simulation; generated when not provided.
    """

    def __init__(
        self,
        pump: Pump,
        name: str = "pump",
        process_simulation_id: PumpProcessSimulationId | None = None,
    ):
        self._id: Final[PumpProcessSimulationId] = process_simulation_id or PumpProcessSimulation._create_id()
        self._name = name
        self._pump = pump

        inlet = LiquidProcessUnit(LiquidProcessUnitType.INLET, "inlet")
        mixer = LiquidProcessUnit(LiquidProcessUnitType.DIRECT_MIXER, "recirculation_mixer")
        pump_unit = LiquidProcessUnit(LiquidProcessUnitType.PUMP, name, id=self._pump.get_id())
        splitter = LiquidProcessUnit(LiquidProcessUnitType.DIRECT_SPLITTER, "recirculation_splitter")
        choke = LiquidProcessUnit(LiquidProcessUnitType.CHOKE, "choke")
        outlet = LiquidProcessUnit(LiquidProcessUnitType.OUTLET, "outlet")
        self._units: Final[tuple[LiquidProcessUnit, ...]] = (inlet, mixer, pump_unit, splitter, choke, outlet)

        # Serial connections, in flow order; connection[i] carries stream[i] (see _project_streams).
        self._connections: Final[tuple[ProcessUnitConnection, ...]] = (
            ProcessUnitConnection(from_process_unit_id=inlet.get_id(), to_process_unit_id=mixer.get_id()),
            ProcessUnitConnection(from_process_unit_id=mixer.get_id(), to_process_unit_id=pump_unit.get_id()),
            ProcessUnitConnection(from_process_unit_id=pump_unit.get_id(), to_process_unit_id=splitter.get_id()),
            ProcessUnitConnection(from_process_unit_id=splitter.get_id(), to_process_unit_id=choke.get_id()),
            ProcessUnitConnection(from_process_unit_id=choke.get_id(), to_process_unit_id=outlet.get_id()),
        )
        self._recirculation_loop: Final[LiquidRecirculationLoop] = LiquidRecirculationLoop(
            splitter_id=splitter.get_id(),
            mixer_id=mixer.get_id(),
        )

    def get_id(self) -> PumpProcessSimulationId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_process_units(self) -> Sequence[LiquidProcessUnit]:
        return self._units

    def get_process_unit_connections(self) -> Sequence[ProcessUnitConnection]:
        return self._connections

    def get_recirculation_loop(self) -> LiquidRecirculationLoop:
        return self._recirculation_loop

    def get_pump_chart(self) -> Chart:
        """The pump node's chart, the static data that defines the pump unit (curves, envelope)."""
        return self._pump.pump_chart

    def get_minimum_flow_rate_m3_per_hour(self) -> float:
        """The pump node's minimum flow [m3/h], the fixed recirculation floor."""
        return self._pump.minimum_flow_rate_m3_per_hour

    @classmethod
    def _create_id(cls: type[Self]) -> PumpProcessSimulationId:
        return PumpProcessSimulationId(ecalc_id_generator())

    def evaluate(self, operating_inputs: Sequence[PumpOperatingInput]) -> tuple[PumpOperatingResult, ...]:
        return tuple(self._evaluate_one(operating_input) for operating_input in operating_inputs)

    def _evaluate_one(self, operating_input: PumpOperatingInput) -> PumpOperatingResult:
        pump_result = self._pump.evaluate(
            inlet_stream=operating_input.inlet_stream,
            discharge_pressure_bara=operating_input.required_discharge_pressure_bara,
        )
        return PumpOperatingResult(
            pump_result=pump_result,
            connection_streams=self._project_streams(pump_result),
        )

    def _project_streams(self, pump_result: PumpEvaluationResult) -> Mapping[ProcessUnitConnectionId, LiquidStream]:
        """Project the closed-form pump result onto the stream of each serial connection.

        Recirculation raises the operating rate between the mixer and the splitter; the requested
        rate is restored downstream. The choke drops the operating discharge pressure to
        the required discharge pressure when the pump over-delivers head.
        """
        requested_stream = pump_result.inlet_stream
        operating_stream_at_suction = requested_stream.with_mass_rate(
            pump_result.operational_volumetric_rate_m3_per_hour * requested_stream.density_kg_per_m3
        )
        operating_stream_after_pump = operating_stream_at_suction.with_pressure(
            pump_result.operational_discharge_pressure_bara
        )
        delivered_stream_before_choke = requested_stream.with_pressure(pump_result.operational_discharge_pressure_bara)
        delivered_pressure_bara = min(
            pump_result.operational_discharge_pressure_bara,
            pump_result.required_discharge_pressure_bara,
        )
        delivered_stream_after_choke = requested_stream.with_pressure(delivered_pressure_bara)

        streams = (
            requested_stream,
            operating_stream_at_suction,
            operating_stream_after_pump,
            delivered_stream_before_choke,
            delivered_stream_after_choke,
        )
        return MappingProxyType(
            {connection.get_id(): stream for connection, stream in zip(self._connections, streams, strict=True)}
        )
