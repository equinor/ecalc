"""System + State: build a graph of units and forward-simulate it in one pass.

``evaluate(overrides, feeds)`` is a pure function: same inputs -> same State,
units unchanged afterwards. It walks the units in flow order, reads each unit's
parameters through the immutable overrides view, calls ``compute`` once, and
records the stream at every port. Capacity exceptions from the compression
kernel are caught ONCE here and returned as a ``CapacityViolation`` on a partial
State — they never escape.

``evaluate`` also accepts an optional contiguous ``section`` (a slice of the
unit order) and an ``inlet`` stream injected at the section's first unit, used
by the solver when solving sections in sequence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import (
    OutsideCapacityError,
    RateTooHighError,
    RateTooLowError,
)
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.units import (
    IN,
    OUT,
    CommonASVLoop,
    Ctx,
    OperatingPoint,
    Overrides,
    Unit,
    _LoopMixer,
    _LoopSplitter,
)

PortKey = tuple[Unit, str]


class ViolationKind(Enum):
    RATE_TOO_LOW = "rate_too_low"
    RATE_TOO_HIGH = "rate_too_high"
    OTHER = "other"


@dataclass(frozen=True)
class CapacityViolation:
    """An outside-chart condition, carried as data rather than raised."""

    unit: Unit
    kind: ViolationKind
    actual: float | None
    bound: float | None
    inlet_stream: FluidStream | None
    reason: str = ""


@dataclass
class State:
    feasible: bool
    streams: Mapping[PortKey, FluidStream]
    operating_points: Mapping[Unit, OperatingPoint]
    violation: CapacityViolation | None = None

    def out(self, unit: Unit, port: str = OUT) -> FluidStream:
        return self.streams[(unit, port)]

    def inlet(self, unit: Unit, port: str = IN) -> FluidStream:
        return self.streams[(unit, port)]

    def result(self, unit: Unit) -> OperatingPoint:
        return self.operating_points[unit]


@dataclass(frozen=True)
class _Edge:
    source: PortKey
    target: PortKey


class ProcessSystem:
    """A graph of units (flow order), their edges, and named feeds."""

    def __init__(self, fluid_service: FluidService, units: Sequence[Unit]):
        self._fluid_service = fluid_service
        self.units: list[Unit] = list(units)
        self._edges: list[_Edge] = []
        self._feeds: dict[PortKey, str] = {}
        self._loop_span: dict[Unit, CommonASVLoop] = {}

    @property
    def fluid_service(self) -> FluidService:
        return self._fluid_service

    # ------------------------------------------------------------- construction

    def _ensure_unit(self, unit: Unit) -> None:
        if unit not in self.units:
            self.units.append(unit)

    def connect(self, from_unit: Unit, to_unit: Unit, from_port: str = OUT, to_port: str = IN) -> ProcessSystem:
        self._ensure_unit(from_unit)
        self._ensure_unit(to_unit)
        self._edges.append(_Edge(source=(from_unit, from_port), target=(to_unit, to_port)))
        return self

    def feed_into(self, unit: Unit, feed_name: str, port: str = IN) -> ProcessSystem:
        self._ensure_unit(unit)
        self._feeds[(unit, port)] = feed_name
        return self

    def _index(self, unit: Unit) -> int:
        return self.units.index(unit)

    def loop_for(self, unit: Unit) -> CommonASVLoop | None:
        """The common recirculation loop wrapping ``unit``, if any."""
        return self._loop_span.get(unit)

    def _compute_loop_spans(self) -> None:
        """Map each unit between a loop's add/remove views to that loop."""
        self._loop_span.clear()
        adders: dict[CommonASVLoop, int] = {}
        for index, unit in enumerate(self.units):
            if isinstance(unit, _LoopMixer):
                adders[unit.loop] = index
            elif isinstance(unit, _LoopSplitter) and unit.loop in adders:
                start = adders[unit.loop]
                for inner in self.units[start + 1 : index]:
                    self._loop_span[inner] = unit.loop

    # ------------------------------------------------------------- evaluation

    def _incoming(self) -> dict[PortKey, PortKey]:
        return {edge.target: edge.source for edge in self._edges}

    def evaluate(
        self,
        overrides: Mapping[Param, float],
        feeds: Mapping[str, FluidStream],
        *,
        section: Sequence[Unit] | None = None,
        inlet: FluidStream | None = None,
    ) -> State:
        ctx = Ctx(self._fluid_service, Overrides(overrides))
        units = list(section) if section is not None else self.units
        incoming = self._incoming()
        streams: dict[PortKey, FluidStream] = {}

        for index, unit in enumerate(units):
            inlets: dict[str, FluidStream] = {}
            for port_name in unit.in_ports:
                target: PortKey = (unit, port_name)
                if index == 0 and port_name == IN and inlet is not None:
                    stream = inlet
                elif target in self._feeds:
                    feed_name = self._feeds[target]
                    if feed_name not in feeds:
                        raise ValueError(f"Missing feed stream '{feed_name}'.")
                    stream = feeds[feed_name]
                else:
                    source = incoming.get(target)
                    if source is None or source not in streams:
                        raise ValueError(
                            f"No stream available for port '{port_name}' of {type(unit).__name__}"
                            f" (in-port has no edge or feed; a section run must start at a boundary)."
                        )
                    stream = streams[source]
                inlets[port_name] = stream
                streams[target] = stream

            try:
                outlets = unit.compute(inlets, ctx)
            except RateTooLowError as error:
                return self._infeasible(unit, ViolationKind.RATE_TOO_LOW, error, inlets, streams, ctx)
            except RateTooHighError as error:
                return self._infeasible(unit, ViolationKind.RATE_TOO_HIGH, error, inlets, streams, ctx)
            except OutsideCapacityError as error:
                violation = CapacityViolation(
                    unit=unit,
                    kind=ViolationKind.OTHER,
                    actual=None,
                    bound=None,
                    inlet_stream=inlets.get(IN),
                    reason=getattr(error, "reason", "") or "",
                )
                return State(False, streams, dict(ctx.operating_points), violation)

            for port_name, stream in outlets.items():
                streams[(unit, port_name)] = stream

        return State(True, streams, dict(ctx.operating_points), None)

    @staticmethod
    def _infeasible(
        unit: Unit,
        kind: ViolationKind,
        error: RateTooLowError | RateTooHighError,
        inlets: Mapping[str, FluidStream],
        streams: Mapping[PortKey, FluidStream],
        ctx: Ctx,
    ) -> State:
        violation = CapacityViolation(
            unit=unit,
            kind=kind,
            actual=error.actual_rate,
            bound=error.boundary_rate,
            inlet_stream=inlets.get(IN),
            reason=getattr(error, "reason", "") or "",
        )
        return State(False, dict(streams), dict(ctx.operating_points), violation)


def chain(*items: object, fluid_service: FluidService) -> ProcessSystem:
    """Build a main-line system. First item may be a feed name (str); rest are units.

    Consecutive units are wired ``out -> in``. A leading feed-name string attaches
    that feed to the first unit's main inlet. The fluid service is the
    thermodynamics seam carried into every ``compute``.
    """
    if not items:
        raise ValueError("chain() needs at least one item.")

    feed_name: str | None = None
    units: list[Unit] = []
    for item in items:
        if isinstance(item, str):
            if units or feed_name is not None:
                raise ValueError("A feed name may only appear as the first chain() item.")
            feed_name = item
        elif isinstance(item, Unit):
            units.append(item)
        else:
            raise ValueError(f"chain() items must be a feed name or Unit, got {type(item).__name__}.")

    if not units:
        raise ValueError("chain() needs at least one unit.")

    system = ProcessSystem(fluid_service=fluid_service, units=units)
    if feed_name is not None:
        system.feed_into(units[0], feed_name, IN)
    for upstream, downstream in zip(units, units[1:], strict=False):
        system.connect(upstream, downstream, OUT, IN)
    system._compute_loop_spans()
    return system
