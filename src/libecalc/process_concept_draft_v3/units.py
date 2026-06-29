"""Units: a dataclass of parameters plus a pure ``compute(inlets) -> outlets``.

Each unit type is its own input spec — there is no separate spec store or
adapter layer. ``compute`` reads the unit's settable fields *through* the
overrides view on ``Ctx`` (``ctx.value(self, "field")``) so the system can
evaluate with an immutable ``{Param: value}`` map without mutating the units.
All thermodynamics go through ``ctx.fluid_service``; the kernels are imported
from ``libecalc.process`` — nothing is copied.

The ``CompressorStage`` is the composite workhorse: it internalizes the
rate-modifier pair as ``add_rate``/``remove_rate`` driven by one
``recirculation_rate`` parameter. The wrapping order matters: recycle
re-enters *before* the cooler. Rate-only mixing is exact — composition is
invariant through cooler and compressor.
"""

from __future__ import annotations

import abc
from collections.abc import Mapping
from dataclasses import dataclass, field

from libecalc.common.units import UnitConstants
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_units.choke import Choke as _ChokeKernel
from libecalc.process.process_units.compressor import Compressor as _CompressorKernel
from libecalc.process.process_units.liquid_remover import LiquidRemover as _LiquidRemoverKernel
from libecalc.process.process_units.mixer import Mixer as _MixerKernel
from libecalc.process.process_units.splitter import Splitter as _SplitterKernel
from libecalc.process_concept_draft_v3.params import UNSET, Param, Unset

IN = "in"
OUT = "out"
SIDE_IN = "side_in"
SIDE_OUT = "side_out"

JOULE_PER_HOUR_TO_MEGAWATT = 1 / 3.6e9


@dataclass(frozen=True)
class OperatingPoint:
    """A compressor stage's position relative to its chart at one evaluation."""

    actual_rate_m3h: float
    minimum_rate_m3h: float
    maximum_rate_m3h: float
    power_mw: float

    @property
    def surge_margin_m3h(self) -> float:
        return self.actual_rate_m3h - self.minimum_rate_m3h

    @property
    def stonewall_margin_m3h(self) -> float:
        return self.maximum_rate_m3h - self.actual_rate_m3h


class Overrides:
    """Read-through view of ``{Param: value}`` over the units' own fields."""

    def __init__(self, mapping: Mapping[Param, float]):
        self._mapping = mapping

    def value(self, owner: object, field_name: str) -> float:
        param = Param(owner, field_name)
        if param in self._mapping:
            return self._mapping[param]
        return getattr(owner, field_name)


class Ctx:
    """Per-evaluation context: the fluid service, the overrides, an observation sink."""

    def __init__(self, fluid_service: FluidService, overrides: Overrides):
        self.fluid_service = fluid_service
        self.overrides = overrides
        self.operating_points: dict[Unit, OperatingPoint] = {}

    def value(self, owner: object, field_name: str) -> float:
        return self.overrides.value(owner, field_name)

    def record(self, unit: Unit, point: OperatingPoint) -> None:
        self.operating_points[unit] = point


class Shaft:
    """Shared object carrying the single speed parameter; NOT a graph node."""

    def __init__(self, speed: float | Unset = UNSET):
        self.speed: float | Unset = speed

    def __repr__(self) -> str:
        return f"Shaft(speed={self.speed!r})"


class Unit(abc.ABC):
    """One node: parameters (its dataclass fields) plus a pure ``compute``."""

    in_ports: tuple[str, ...] = (IN,)
    out_ports: tuple[str, ...] = (OUT,)

    @abc.abstractmethod
    def compute(self, inlets: Mapping[str, FluidStream], ctx: Ctx) -> dict[str, FluidStream]: ...


def add_rate(stream: FluidStream, rate_sm3_per_day: float) -> FluidStream:
    """Rate-only mix: add standard rate, composition unchanged."""
    added_mass = rate_sm3_per_day * stream.standard_density_gas_phase_after_flash / UnitConstants.HOURS_PER_DAY
    return stream.with_mass_rate(stream.mass_rate_kg_per_h + added_mass)


def remove_rate(stream: FluidStream, rate_sm3_per_day: float) -> FluidStream:
    """Rate-only split: remove standard rate, composition unchanged."""
    removed_mass = rate_sm3_per_day * stream.standard_density_gas_phase_after_flash / UnitConstants.HOURS_PER_DAY
    return stream.with_mass_rate(stream.mass_rate_kg_per_h - removed_mass)


@dataclass(eq=False)
class CompressorStage(Unit):
    """cooler + scrubber + compressor + ASV-as-parameter — the composite stage.

    Compute order is load-bearing: recycle mixes in BEFORE the cooler, and is
    removed again after compression.
    """

    chart: ChartData
    shaft: Shaft
    inlet_temperature_kelvin: float | None = 303.15  # None = no cooler
    remove_liquid: bool = False
    recirculation_rate: float = 0.0  # sm3/day; auto-controlled (anti-surge) by default

    _kernel: _CompressorKernel | None = field(default=None, init=False, repr=False, compare=False)
    _liquid_remover: _LiquidRemoverKernel | None = field(default=None, init=False, repr=False, compare=False)

    def _compressor(self, fluid_service: FluidService) -> _CompressorKernel:
        if self._kernel is None:
            self._kernel = _CompressorKernel(compressor_chart=self.chart, fluid_service=fluid_service)
        return self._kernel

    def _speed(self, ctx: Ctx) -> float:
        speed = ctx.value(self.shaft, "speed")
        if speed is UNSET:
            raise ValueError(
                "Shaft speed is UNSET; set it on the Shaft or provide it as a solver override (Param(shaft, 'speed'))."
            )
        return float(speed)

    def _cool(self, stream: FluidStream, ctx: Ctx) -> FluidStream:
        temperature = self.inlet_temperature_kelvin
        if temperature is None or stream.temperature_kelvin == temperature:
            return stream
        new_fluid = ctx.fluid_service.create_fluid(stream.fluid_model, stream.pressure_bara, temperature)
        return stream.with_new_fluid(new_fluid)

    def _scrub(self, stream: FluidStream, ctx: Ctx) -> FluidStream:
        if not self.remove_liquid:
            return stream
        if self._liquid_remover is None:
            self._liquid_remover = _LiquidRemoverKernel(fluid_service=ctx.fluid_service)
        return self._liquid_remover.propagate_stream(stream)

    def compute(self, inlets: Mapping[str, FluidStream], ctx: Ctx) -> dict[str, FluidStream]:
        recirculation_rate = float(ctx.value(self, "recirculation_rate"))
        speed = self._speed(ctx)
        kernel = self._compressor(ctx.fluid_service)
        kernel.set_speed(speed)

        stream = add_rate(inlets[IN], recirculation_rate)
        stream = self._cool(stream, ctx)
        stream = self._scrub(stream, ctx)

        compressor_inlet = stream
        outlet = kernel.propagate_stream(compressor_inlet)
        ctx.record(
            self,
            OperatingPoint(
                actual_rate_m3h=compressor_inlet.volumetric_rate_m3_per_hour,
                minimum_rate_m3h=kernel.minimum_flow_rate,
                maximum_rate_m3h=kernel.maximum_flow_rate,
                power_mw=(outlet.enthalpy_joule_per_kg - compressor_inlet.enthalpy_joule_per_kg)
                * compressor_inlet.mass_rate_kg_per_h
                * JOULE_PER_HOUR_TO_MEGAWATT,
            ),
        )
        return {OUT: remove_rate(outlet, recirculation_rate)}

    def compressor_inlet(self, stage_inlet: FluidStream, recirculation_rate: float, ctx_fluid) -> FluidStream:
        """Reconstruct the stream entering the compression step (add_rate -> cool -> scrub).

        Standard rate is composition-invariant through cooling, so a recirculation
        rate added here equals the same standard rate added at the stage entry.
        """
        stream = add_rate(stage_inlet, recirculation_rate)
        temperature = self.inlet_temperature_kelvin
        if temperature is not None and stream.temperature_kelvin != temperature:
            stream = stream.with_new_fluid(
                ctx_fluid.create_fluid(stream.fluid_model, stream.pressure_bara, temperature)
            )
        if self.remove_liquid:
            if self._liquid_remover is None:
                self._liquid_remover = _LiquidRemoverKernel(fluid_service=ctx_fluid)
            stream = self._liquid_remover.propagate_stream(stream)
        return stream

    def recirculation_range(self, inlet_stream: FluidStream, speed: float, fluid_service: FluidService) -> Boundary:
        """Additional standard rate [sm3/day] needed (min) / available (max) at ``speed``.

        Port of ``Compressor.get_recirculation_range`` including the
        ``RECIRCULATION_BOUNDARY_TOLERANCE`` nudges.
        """
        kernel = self._compressor(fluid_service)
        kernel.set_speed(speed)
        return kernel.get_recirculation_range(inlet_stream)

    def standard_rate_range(self, inlet_stream: FluidStream, speed: float, fluid_service: FluidService) -> Boundary:
        """Absolute min/max standard rate [sm3/day] the stage admits at ``speed`` (nudged)."""
        kernel = self._compressor(fluid_service)
        kernel.set_speed(speed)
        return Boundary(
            min=kernel.get_minimum_standard_rate(inlet_stream),
            max=kernel.get_maximum_standard_rate(inlet_stream),
        )


@dataclass(eq=False)
class Choke(Unit):
    """Throttling valve: subtracts ``delta_pressure`` (bara). 0 = wide open."""

    delta_pressure: float = 0.0

    _kernel: _ChokeKernel | None = field(default=None, init=False, repr=False, compare=False)

    def compute(self, inlets: Mapping[str, FluidStream], ctx: Ctx) -> dict[str, FluidStream]:
        if self._kernel is None:
            self._kernel = _ChokeKernel(fluid_service=ctx.fluid_service)
        self._kernel.set_pressure_change(float(ctx.value(self, "delta_pressure")))
        return {OUT: self._kernel.propagate_stream(inlets[IN])}


@dataclass(eq=False)
class Cooler(Unit):
    """Standalone cooler/heater to a fixed outlet temperature."""

    outlet_temperature_kelvin: float = 303.15

    def compute(self, inlets: Mapping[str, FluidStream], ctx: Ctx) -> dict[str, FluidStream]:
        temperature = float(ctx.value(self, "outlet_temperature_kelvin"))
        stream = inlets[IN]
        if stream.temperature_kelvin == temperature:
            return {OUT: stream}
        new_fluid = ctx.fluid_service.create_fluid(stream.fluid_model, stream.pressure_bara, temperature)
        return {OUT: stream.with_new_fluid(new_fluid)}


@dataclass(eq=False)
class LiquidRemover(Unit):
    """Standalone scrubber: drops out the liquid phase."""

    _kernel: _LiquidRemoverKernel | None = field(default=None, init=False, repr=False, compare=False)

    def compute(self, inlets: Mapping[str, FluidStream], ctx: Ctx) -> dict[str, FluidStream]:
        if self._kernel is None:
            self._kernel = _LiquidRemoverKernel(fluid_service=ctx.fluid_service)
        return {OUT: self._kernel.propagate_stream(inlets[IN])}


@dataclass(eq=False)
class Splitter(Unit):
    """Removes a fixed standard rate; remainder on ``out``, offtake on ``side_out``."""

    offtake_rate_sm3_per_day: float = 0.0

    out_ports: tuple[str, ...] = field(default=(OUT, SIDE_OUT), init=False, repr=False, compare=False)
    _kernel: _SplitterKernel | None = field(default=None, init=False, repr=False, compare=False)

    def compute(self, inlets: Mapping[str, FluidStream], ctx: Ctx) -> dict[str, FluidStream]:
        if self._kernel is None:
            self._kernel = _SplitterKernel(fluid_service=ctx.fluid_service)
        self._kernel.set_rate(float(ctx.value(self, "offtake_rate_sm3_per_day")))
        inlet = inlets[IN]
        return {OUT: self._kernel.propagate_stream(inlet), SIDE_OUT: self._kernel.get_split_stream(inlet)}


@dataclass(eq=False)
class Mixer(Unit):
    """Mixes a side stream (``side_in``) into the through-stream (full composition)."""

    in_ports: tuple[str, ...] = field(default=(IN, SIDE_IN), init=False, repr=False, compare=False)
    _kernel: _MixerKernel | None = field(default=None, init=False, repr=False, compare=False)

    def compute(self, inlets: Mapping[str, FluidStream], ctx: Ctx) -> dict[str, FluidStream]:
        if self._kernel is None:
            self._kernel = _MixerKernel(fluid_service=ctx.fluid_service)
        self._kernel.set_stream(inlets[SIDE_IN])
        return {OUT: self._kernel.propagate_stream(inlets[IN])}


class _LoopMixer(Unit):
    """Upstream half of a cross-stage common loop; adds the shared loop rate."""

    def __init__(self, loop: CommonASVLoop):
        self.loop = loop

    def compute(self, inlets: Mapping[str, FluidStream], ctx: Ctx) -> dict[str, FluidStream]:
        rate = float(ctx.value(self.loop, "rate_sm3_per_day"))
        return {OUT: add_rate(inlets[IN], rate)}


class _LoopSplitter(Unit):
    """Downstream half of a cross-stage common loop; removes the shared loop rate."""

    def __init__(self, loop: CommonASVLoop):
        self.loop = loop

    def compute(self, inlets: Mapping[str, FluidStream], ctx: Ctx) -> dict[str, FluidStream]:
        rate = float(ctx.value(self.loop, "rate_sm3_per_day"))
        return {OUT: remove_rate(inlets[IN], rate)}


class CommonASVLoop:
    """Cross-stage common ASV: one shared rate driving a mixer/splitter pair.

    NOT a unit itself. ``loop.inlet`` and ``loop.outlet`` are two tiny unit views
    over the same ``rate_sm3_per_day`` parameter. The handle is
    ``Param(loop, "rate_sm3_per_day")``.
    """

    def __init__(self, rate_sm3_per_day: float = 0.0):
        self.rate_sm3_per_day = rate_sm3_per_day
        self._inlet = _LoopMixer(self)
        self._outlet = _LoopSplitter(self)

    @property
    def inlet(self) -> _LoopMixer:
        return self._inlet

    @property
    def outlet(self) -> _LoopSplitter:
        return self._outlet
