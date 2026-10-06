---
slug: "nextgen-changelog"
title: "NextGen"
authors: ecalc-team
tags: [release, eCalc, nextgen]
sidebar_position: 0
---

# eCalc NextGen

Changes to the NextGen YAML types: `FLUIDS`, `PROCESS_SIMULATIONS`, `PUMP_PROCESS_SIMULATIONS` and `ENERGY_NETWORK`.
These are not available in legacy models, so they are not part of the release changelogs.

## v15.0 {/* #v15-0 */}

- `PROCESS_SIMULATIONS`: solver constraints use a relative tolerance, improving convergence for large values.
- `ENERGY_NETWORK`: capacities can be expressions, and capacity shortfalls are reported.
- `ENERGY_NETWORK`: junctions allocate demand across multiple inputs, with per-input dispatch limits.
- `ENERGY_NETWORK`: added `COMPRESSOR_SAMPLED` units. Sampled compressor tables extrapolate using the convex hull of the sampled data.
- `ENERGY_NETWORK`: `GAS_TURBINE` requires a `MODEL`, a turbine defined under `DEFINITIONS.TURBINES` or in place, with load/efficiency data given directly or in a `FILE`. Fuel is calculated from the turbine curve, and the curve limits the turbine capacity. Demand below the lowest load in the curve burns the fuel of the lowest load, and zero demand burns no fuel. `MODEL` no longer accepts a facility model name (`MODELS: TURBINE`); it was previously ignored.
- `ENERGY_NETWORK`: `GENERATOR_SET` requires a `MODEL`, a generator set defined under `DEFINITIONS.GENERATOR_SETS` or in place, with power/fuel data given directly or in a `FILE`. Fuel is interpolated from the curve as for the legacy generator set, and the curve limits the generator set capacity. `MODEL` no longer accepts a facility model name; it was previously ignored.

## v14.0 {/* #v14-0 */}

- Added the `ENERGY_NETWORK` YAML types (sources, consumers, converters, junctions and cables), with a reference and examples.
- `ENERGY_NETWORK` models are evaluated, so energy demand and flow are solved from the YAML.
- `PUMP_PROCESS_SIMULATIONS`: pump head is bounded by the maximum head of the pump chart, not only the minimum. Power and pressure no longer grow without limit outside the chart.

## v13.12 {/* #v13-12 */}

- Added top-level `FLUIDS`, so process simulations can reuse named fluid compositions.

## v13.10 {/* #v13-10 */}

- Added `PUMP_PROCESS_SIMULATIONS` for liquid pumps, calculated from a pump chart, an inlet stream and the required discharge pressure.

## v13.8 {/* #v13-8 */}

- `PROCESS_SIMULATIONS`: added `MIXER` and `SPLITTER` units.

## v13.4 {/* #v13-4 */}

- `PROCESS_SIMULATIONS`: added `COMPRESSOR` units, solved against the compressor chart.

## Groundwork before v13.4 {/* #groundwork */}

Process simulations could not be run in these versions. They only contain internal preparation for `PROCESS_SIMULATIONS`.

- **v13.4.0:** pressure control strategies (common and individual ASV, upstream and downstream choke), anti-surge strategies, a stream propagator, and ids for process units and systems.
- **v13.1.0:** `PROCESS_SIMULATIONS` process constraints in the YAML schema, and the common ASV and recirculation solvers.
- **v13.0.3:** a new process system interface. The top-level `PROCESS_SIMULATIONS` keyword was added to the YAML schema, without a mapping to the model.
