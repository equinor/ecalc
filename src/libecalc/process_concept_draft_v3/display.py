"""Display topology — the frontend contract (plan §9).

The solving graph is not what users see. The backend persists, and the frontend
visualizes, a flat unit list with explicit ASV hardware (DIRECT_MIXER/
DIRECT_SPLITTER), connections with port numbers, recirculation loops as
splitter->mixer references, and shafts as compressor-id groups.

``display_topology`` expands each ``CompressorStage`` deterministically into
cooler / scrubber / compressor (+ its DIRECT_MIXER/DIRECT_SPLITTER pair only when
its recirculation parameter is LIVE — referenced by a constraint, or auto under
the controller, i.e. NOT idle inside a common loop's span). The common
``loop.inlet``/``loop.outlet`` pair emits as the single train-wide mixer/splitter.
v3 does not import the engine repo — it emits plain dataclasses shaped to map 1:1.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.system import ProcessSystem
from libecalc.process_concept_draft_v3.units import (
    Choke,
    CompressorStage,
    Cooler,
    LiquidRemover,
    Mixer,
    Shaft,
    Splitter,
    Unit,
    _LoopMixer,
    _LoopSplitter,
)

MAIN_PORT = 0
SIDE_PORT = 1


class DisplayUnitKind(StrEnum):
    COMPRESSOR = "compressor"
    CHOKE = "choke"
    TEMPERATURE_SETTER = "temperature_setter"
    DIRECT_MIXER = "direct_mixer"
    DIRECT_SPLITTER = "direct_splitter"
    LIQUID_REMOVER = "liquid_remover"
    SPLITTER = "splitter"
    MIXER = "mixer"


@dataclass(frozen=True)
class DisplayUnit:
    id: str
    kind: DisplayUnitKind
    source: object


@dataclass(frozen=True)
class DisplayConnection:
    from_id: str
    from_port: int
    to_id: str
    to_port: int


@dataclass(frozen=True)
class DisplayLoop:
    id: str
    splitter_id: str
    mixer_id: str


@dataclass(frozen=True)
class DisplayShaft:
    id: str
    compressor_ids: tuple[str, ...]


@dataclass(frozen=True)
class DisplayTopology:
    units: tuple[DisplayUnit, ...]
    connections: tuple[DisplayConnection, ...]
    loops: tuple[DisplayLoop, ...]
    shafts: tuple[DisplayShaft, ...]


def _referenced_recirculation_params(constraints: Sequence) -> set[Param]:
    referenced: set[Param] = set()

    def visit(constraint) -> None:
        if constraint is None:
            return
        vary = constraint.vary
        if isinstance(vary, Param):
            referenced.add(vary)
        else:  # CoupledParameter
            referenced.update(getattr(vary, "params", ()))
        visit(constraint.fallback)

    for constraint in constraints:
        visit(constraint)
    return referenced


def _stage_recirculation_is_live(system: ProcessSystem, stage: CompressorStage, referenced: set[Param]) -> bool:
    if Param(stage, "recirculation_rate") in referenced:
        return True
    # Idle by configuration when wrapped by a common loop; otherwise the controller owns it.
    return system.loop_for(stage) is None


class _IdAllocator:
    def __init__(self) -> None:
        self._count = 0

    def allocate(self, kind: DisplayUnitKind, source: object) -> DisplayUnit:
        unit = DisplayUnit(id=f"{kind.value}-{self._count}", kind=kind, source=source)
        self._count += 1
        return unit


def display_topology(system: ProcessSystem, constraints: Sequence = ()) -> DisplayTopology:
    referenced = _referenced_recirculation_params(constraints)
    allocator = _IdAllocator()

    units: list[DisplayUnit] = []
    connections: list[DisplayConnection] = []
    loops: list[DisplayLoop] = []
    # Per source object: (first_display_id, last_display_id) for external wiring.
    endpoints: dict[Unit, tuple[str, str]] = {}
    shaft_compressors: dict[Shaft, list[str]] = {}
    pending_loop_mixer: dict[object, str] = {}

    for source in system.units:
        emitted: list[DisplayUnit] = []

        if isinstance(source, CompressorStage):
            live = _stage_recirculation_is_live(system, source, referenced)
            mixer = splitter = None
            if live:
                mixer = allocator.allocate(DisplayUnitKind.DIRECT_MIXER, source)
                emitted.append(mixer)
            if source.inlet_temperature_kelvin is not None:
                emitted.append(allocator.allocate(DisplayUnitKind.TEMPERATURE_SETTER, source))
            if source.remove_liquid:
                emitted.append(allocator.allocate(DisplayUnitKind.LIQUID_REMOVER, source))
            compressor = allocator.allocate(DisplayUnitKind.COMPRESSOR, source)
            emitted.append(compressor)
            if live:
                splitter = allocator.allocate(DisplayUnitKind.DIRECT_SPLITTER, source)
                emitted.append(splitter)
                assert mixer is not None
                loops.append(DisplayLoop(id=f"loop-{len(loops)}", splitter_id=splitter.id, mixer_id=mixer.id))
            shaft_compressors.setdefault(source.shaft, []).append(compressor.id)

        elif isinstance(source, _LoopMixer):
            unit = allocator.allocate(DisplayUnitKind.DIRECT_MIXER, source)
            emitted.append(unit)
            pending_loop_mixer[source.loop] = unit.id
        elif isinstance(source, _LoopSplitter):
            unit = allocator.allocate(DisplayUnitKind.DIRECT_SPLITTER, source)
            emitted.append(unit)
            mixer_id = pending_loop_mixer.get(source.loop)
            if mixer_id is not None:
                loops.append(DisplayLoop(id=f"loop-{len(loops)}", splitter_id=unit.id, mixer_id=mixer_id))
        elif isinstance(source, Choke):
            emitted.append(allocator.allocate(DisplayUnitKind.CHOKE, source))
        elif isinstance(source, Cooler):
            emitted.append(allocator.allocate(DisplayUnitKind.TEMPERATURE_SETTER, source))
        elif isinstance(source, LiquidRemover):
            emitted.append(allocator.allocate(DisplayUnitKind.LIQUID_REMOVER, source))
        elif isinstance(source, Splitter):
            emitted.append(allocator.allocate(DisplayUnitKind.SPLITTER, source))
        elif isinstance(source, Mixer):
            emitted.append(allocator.allocate(DisplayUnitKind.MIXER, source))
        else:
            emitted.append(allocator.allocate(DisplayUnitKind.COMPRESSOR, source))

        units.extend(emitted)
        # Internal main-line wiring within an expanded source.
        for upstream, downstream in zip(emitted, emitted[1:], strict=False):
            connections.append(DisplayConnection(upstream.id, MAIN_PORT, downstream.id, MAIN_PORT))
        endpoints[source] = (emitted[0].id, emitted[-1].id)

    # External wiring: map each system edge onto the display endpoints, carrying port numbers.
    for edge in system._edges:  # noqa: SLF001 (display reads the system's own topology)
        from_unit, from_port = edge.source
        to_unit, to_port = edge.target
        if from_unit not in endpoints or to_unit not in endpoints:
            continue
        from_id = endpoints[from_unit][1]
        to_id = endpoints[to_unit][0]
        connections.append(
            DisplayConnection(
                from_id=from_id,
                from_port=SIDE_PORT if from_port.startswith("side") else MAIN_PORT,
                to_id=to_id,
                to_port=SIDE_PORT if to_port.startswith("side") else MAIN_PORT,
            )
        )

    shafts = tuple(
        DisplayShaft(id=f"shaft-{index}", compressor_ids=tuple(compressor_ids))
        for index, (_shaft, compressor_ids) in enumerate(shaft_compressors.items())
    )

    return DisplayTopology(
        units=tuple(units),
        connections=tuple(connections),
        loops=tuple(loops),
        shafts=shafts,
    )
