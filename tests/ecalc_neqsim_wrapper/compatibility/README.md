# NeqSim compatibility suite

NeqSim is a third-party Java library we ship as a jar file. That
arrangement is uncomfortable for several reasons. A new jar can shift the
value of a flash without anyone in the ecalc team being told. When a
NeqSim release regresses — i.e. starts returning different numbers than
it used to for inputs that previously worked — it usually does so
silently. The values look finite and reasonable, but they propagate
through compressor and pressure logic until something crashes far from
the root cause. And we query NeqSim in regions no one hand-checks: up
to 2000 bara at 450 K during max-speed probes, on whatever composition
the user feeds in. The existing application tests do not pin NeqSim's
outputs, so today the only signal that a jar bump broke something is
often an unrelated-looking failure several layers downstream. We would
like to stop being surprised this way.

A compatibility suite should give us three guarantees, in priority order.
A jar bump that changes any output we read should produce a failing test,
named after the (composition, P, T, EoS) state where it changed — not a
slow regression in some integration metric. A wrapper change that breaks
an operation we depend on (flashes, phase extraction, mixing, EoS
differentiation) should fail in the same checkout, not in the next ecalc
run. And an operating point ecalc can plausibly query, where NeqSim
returns garbage, should fail here before that garbage reaches the
compressor solver.

Equally important is what this suite is *not*. It is not an ecalc test
suite — bugs in solver logic, validation, units, caches, or process
units belong in the existing tests. It is not a NeqSim correctness suite
— we are detecting *change*, not certifying *physics*. And it is not run
on every PR; it is deselected by default and runs only when the jar, the
wrapper, or the suite itself changes, or when an engineer asks for it.

Structurally we want three layers, each answering a single question and
all reading from one source of truth for the operating envelope (pressure
range, temperature range, EoS models, compositions). The first layer asks
whether NeqSim returned a sensible number at all — finite, in physical
bounds, no stale defaults in the output — across the full envelope. The
second asks whether NeqSim plays by the rules under the operations we
depend on, with targeted tests that pin each operation's invariants rather
than its exact numerical output. The third asks whether any number we read
has drifted: a snapshot of every property ecalc reads at every state in
the envelope, generated against a known-good jar and reviewed on every
bump.

A failure must name the failing state in a form the engineer can paste
into a notebook to reproduce, and must make clear which layer caught it —
garbage value, broken invariant, or drifted number — without anyone
needing to read test source.

We accept upfront that this design will not catch ecalc-side bugs, bugs
at operating points outside the envelope, drift smaller than the snapshot
tolerance, or regressions in NeqSim operations the wrapper does not
exercise. Those trade-offs are deliberate. The suite is doing its job if
every jar bump PR ends in either a clean run, an explicitly accepted
snapshot diff, or a rejection of the bump — and if we stop finding NeqSim
regressions by way of downstream `NaN` crashes.

The GitHub Actions workflow `test-neqsim-compatibility.yml` gates on jar,
wrapper, suite, and workflow path changes.

## Operating envelope

`envelope.py` is the single source of truth. Every state-generating
helper in this directory reads it from there:

| Dimension     | Range                                                      |
| ------------- | ---------------------------------------------------------- |
| Pressure      | 1 – 2000 bara (`MAX_FIRST_GUESS_BAR` cap on max-speed probes) |
| Temperature   | 250 – 460 K (per-stage PH-flash outlet at off-design)      |
| EoS           | SRK, PR, GERG_SRK, GERG_PR                                 |
| Operations    | TP-flash, PH-flash, remove_liquid, mixing, property extraction |

Three named sub-grids cover three regimes ecalc realistically hits:

- `nominal_grid()` — 1–200 bara × 250–380 K (compressor suction to mid-discharge).
- `high_pressure_grid()` — 300–400 bara × 300–360 K (e.g. Sverdrup gas injection).
- `max_speed_probe_grid()` — 500–2000 bara × 400–450 K (dense-supercritical regime hit during max-speed probes).

When ecalc's envelope changes, update `envelope.py`. Everything
downstream re-derives.

## How it's organised

Three groups, each answering a different question:

1. **`sanity/` — does NeqSim return numbers that look real?**
   Point-wise sanity checks (no NaN, no default kappa, values in
   physical ranges) plus trajectory continuity (density monotonic in
   P on single-phase segments, enthalpy monotonic in T at fixed P).
   Also the external-reference checks for selected (composition, P,
   T, EoS) states with published values, and the structural guard
   that no test parametrises a wet composition below its temperature
   floor.

2. **`behaviour/` — does NeqSim follow the rules our pipeline code
   assumes?** Self-consistency invariants for the operations ecalc
   composes in production: state identities (round-trip, idempotency,
   getter/setter consistency), phase operations (gas-phase extraction
   matches a clean PT flash of the gas-phase composition), flash
   operations (PH-flash returns the requested enthalpy, an enthalpy
   increase raises temperature, a five-stage chain stays well-defined),
   mixing (mass and molar balance), EoS differentiation (SRK vs PR
   produce measurably different densities), and the wrapper's own
   degenerate-state validators.

3. **`regression/` — do the numbers match the previous jar?** A pinned
   reference snapshot (`reference_snapshot.json`) holds every property
   for every cell in the regression spec at strict 1e-9 relative
   tolerance. Any drift fails the test; the fix is either to revert
   the bump or to deliberately regenerate the snapshot with a brief
   justification of the accepted drift.

## Design constraints

These are baked into the state generators. The structural guard
`sanity/test_temperature_floors.py` will fail at collection time if a
new test or pin violates them.

- **No wet composition is flashed below ~273 K.** NeqSim does not
  model the solid water phase. Below water's freezing point a flash
  on a water-bearing composition can return NaN / default kappa /
  non-physical Z, flip phase splits between EoS models, or in some
  jar versions tear down the JVM gateway. The suite therefore
  declines to test wet compositions below a conservative floor of
  **280 K**. The floor lives in
  `compositions.MIN_TEMPERATURE_KELVIN_PER_COMPOSITION` and is
  populated automatically for any composition with `water > 0`.
  Every state generator consults `is_state_supported(name, T)`. To
  probe the cold/high-P region for a heavy composition that is
  normally used wet, add a dry sister composition (see
  `c3_rich_wellstream_dry`).

- **`sanity/` and `behaviour/` use lenient predicates; `regression/`
  is strict.** The sanity and behaviour groups catch categorical
  breakage (NaN, default, non-physical, broken algebraic identities).
  Strict numerical pinning lives only in the regression snapshot.

## Running it

```bash
# Full suite, locally. Targeting the directory auto-enables the
# `neqsim_compat` marker; you don't need `-m neqsim_compat`.
uv run pytest tests/ecalc_neqsim_wrapper/compatibility/

# Just the sanity group.
uv run pytest tests/ecalc_neqsim_wrapper/compatibility/sanity/

# Regenerate the regression snapshot against the currently vendored jar.
uv run pytest tests/ecalc_neqsim_wrapper/compatibility/ --regenerate-neqsim-snapshot
```

The full suite takes around 20 minutes. JVM startup dominates the
first few seconds; the rest is NeqSim flash calls.

## How to react to a failure

1. **Sanity failure** — NeqSim is returning garbage at a state ecalc
   exercises. Either the jar regressed in that region, or the suite
   has hit a documented constraint that should be expressed in the
   floor registry. Look at the failing state first; if it's a
   wet composition below 273 K, the fix is in `compositions.py`,
   not in NeqSim.

2. **Behaviour failure** — NeqSim is returning numbers that violate
   an algebraic identity ecalc relies on (e.g. PH-flash output
   enthalpy doesn't match the input target). This is a real
   regression and blocks the bump.

3. **Regression failure** — A number drifted outside the strict
   tolerance. Investigate before regenerating. If the drift is an
   improvement (e.g. bug fix in a NeqSim correlation), regenerate
   the snapshot and commit it alongside the jar bump with a brief
   justification. If the drift is a quiet correctness loss, block
   the bump.
