"""Continuity checks along pressure and temperature trajectories."""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Sequence

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid

from ..compositions import COMPOSITIONS, min_temperature_kelvin_for

# Fine enough to catch isolated kappa spikes.
PRESSURE_TRAJECTORY_BARA: tuple[float, ...] = tuple(
    1.0 + i * (199.0 / 49) for i in range(50)
)  # 50 points from 1 to 200 bara
PRESSURE_TRAJECTORY_TEMPERATURE_KELVIN: float = 300.0

TEMPERATURE_TRAJECTORY_KELVIN: tuple[float, ...] = tuple(
    240.0 + i * (140.0 / 29) for i in range(30)
)  # 30 points from 240 to 380 K
TEMPERATURE_TRAJECTORY_PRESSURE_BARA: float = 20.0


def _temperature_trajectory_for(composition_name: str) -> tuple[float, ...]:
    floor = min_temperature_kelvin_for(composition_name)
    return tuple(t for t in TEMPERATURE_TRAJECTORY_KELVIN if t >= floor)


def _build_property_series(
    composition_name: str,
    samples: Sequence[tuple[float, float]],
    property_getter: Callable[[NeqsimFluid], float],
) -> tuple[list[float], list[NeqsimFluid]]:
    fluids: list[NeqsimFluid] = []
    values: list[float] = []
    for pressure_bara, temperature_kelvin in samples:
        fluid = NeqsimFluid.create_thermo_system(
            composition=COMPOSITIONS[composition_name],
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
        )
        fluids.append(fluid)
        values.append(property_getter(fluid))
    return values, fluids


def _assert_no_outliers(
    values: Sequence[float],
    *,
    label: str,
    composition_name: str,
    sample_axis_label: str,
    sample_axis_values: Sequence[float],
    relative_outlier_factor: float = 5.0,
) -> None:
    """An interior point may not lie more than `relative_outlier_factor`x
    away (or 1/factor below) the median of its immediate neighbours.

    Catches isolated default-value spikes (e.g. kappa dropping to 1.0 between
    two well-formed values) while permitting genuinely sharp property
    transitions across the dew line.
    """
    assert relative_outlier_factor > 1.0
    for i in range(1, len(values) - 1):
        prev_value, this_value, next_value = values[i - 1], values[i], values[i + 1]
        if not math.isfinite(this_value):
            raise AssertionError(
                f"{label}[{i}] is not finite at "
                f"{composition_name} {sample_axis_label}={sample_axis_values[i]}: {this_value!r}"
            )
        neighbor_median = statistics.median([prev_value, next_value])
        if neighbor_median == 0.0:
            continue
        ratio = this_value / neighbor_median
        assert 1.0 / relative_outlier_factor <= ratio <= relative_outlier_factor, (
            f"{label} outlier at {composition_name} {sample_axis_label}={sample_axis_values[i]}: "
            f"value={this_value!r}, neighbours={(prev_value, next_value)!r}, "
            f"ratio={ratio!r} (limit {relative_outlier_factor}x)"
        )


def _assert_monotonic_increasing(
    values: Sequence[float],
    *,
    label: str,
    composition_name: str,
    sample_axis_label: str,
    sample_axis_values: Sequence[float],
    absolute_tolerance: float = 0.0,
) -> None:
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        assert delta >= -absolute_tolerance, (
            f"{label} not monotonic at {composition_name} "
            f"{sample_axis_label}={sample_axis_values[i]}: "
            f"{values[i - 1]!r} -> {values[i]!r} (delta={delta!r})"
        )


@pytest.mark.parametrize("composition_name", list(COMPOSITIONS))
def test_pressure_trajectory_no_kappa_outliers(composition_name):
    kappas, _ = _build_property_series(
        composition_name,
        [(p, PRESSURE_TRAJECTORY_TEMPERATURE_KELVIN) for p in PRESSURE_TRAJECTORY_BARA],
        lambda f: f.kappa,
    )
    _assert_no_outliers(
        kappas,
        label="kappa",
        composition_name=composition_name,
        sample_axis_label="P[bara]",
        sample_axis_values=PRESSURE_TRAJECTORY_BARA,
    )
    for i, value in enumerate(kappas):
        assert abs(value - 1.0) > 1e-6, (
            f"default kappa at {composition_name} P={PRESSURE_TRAJECTORY_BARA[i]}: {value!r}"
        )


@pytest.mark.parametrize("composition_name", list(COMPOSITIONS))
def test_pressure_trajectory_density_monotonic_in_single_phase(composition_name):
    """Bulk density of a single-phase fluid must increase with pressure at fixed T.

    Restricted to the portion of the trajectory that stays single-phase
    (either vapour fraction >= 0.999 or <= 1e-3 throughout the segment);
    crossing the two-phase envelope introduces a physical bulk-density
    transition that is not in scope here.
    """
    pressures = list(PRESSURE_TRAJECTORY_BARA)
    samples = [(p, PRESSURE_TRAJECTORY_TEMPERATURE_KELVIN) for p in pressures]
    densities, fluids = _build_property_series(composition_name, samples, lambda f: f.density)

    # Ignore physical density jumps across the two-phase envelope.
    def is_single_phase(fluid: NeqsimFluid) -> bool:
        vf = fluid.vapor_fraction_molar
        return vf >= 0.999 or vf <= 1e-3

    flags = [is_single_phase(f) for f in fluids]
    best_start = best_len = 0
    cur_start = 0
    for i, flag in enumerate(flags + [False]):
        if not flag:
            if i - cur_start > best_len:
                best_len = i - cur_start
                best_start = cur_start
            cur_start = i + 1
    if best_len < 5:
        pytest.skip(f"{composition_name}: no single-phase segment of length >=5 in pressure trajectory")
    segment = densities[best_start : best_start + best_len]
    segment_pressures = pressures[best_start : best_start + best_len]
    _assert_monotonic_increasing(
        segment,
        label="density",
        composition_name=composition_name,
        sample_axis_label="P[bara]",
        sample_axis_values=segment_pressures,
        absolute_tolerance=1e-9,
    )


@pytest.mark.parametrize("composition_name", list(COMPOSITIONS))
def test_temperature_trajectory_enthalpy_monotonic_increasing(composition_name):
    """Specific enthalpy must increase with temperature at fixed pressure.

    Holds for both single-phase and two-phase fluids (the latent-heat
    contribution along the two-phase envelope adds to the sensible
    contribution; the total stays monotonic in T).
    """
    trajectory = _temperature_trajectory_for(composition_name)
    enthalpies, _ = _build_property_series(
        composition_name,
        [(TEMPERATURE_TRAJECTORY_PRESSURE_BARA, t) for t in trajectory],
        lambda f: f.enthalpy_joule_per_kg,
    )
    _assert_monotonic_increasing(
        enthalpies,
        label="enthalpy_joule_per_kg",
        composition_name=composition_name,
        sample_axis_label="T[K]",
        sample_axis_values=trajectory,
        # Tolerance for flat numerical segments.
        absolute_tolerance=1.0,
    )
