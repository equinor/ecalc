# process_concept_draft_v3

A re-organization of the process solver. The numerics are
unchanged; the structure is fixed.

## Mental model

- **A unit is a dataclass with parameters and a pure `compute(inlets) -> outlets`.**
  The parameter set *is* the unit's degrees of freedom. No adapters, no separate
  spec store, no calculation modes.
- **Topology is dumb; behavior lives on units.** `ProcessSystem` holds object
  references and edges. References are object handles — `Param(unit, "field")` —
  validated at construction, so invalid references are impossible.
- **Evaluation is a pure function** `system.evaluate(overrides, feeds) -> State`:
  one topological pass, streams at every port, capacity violations as data
  (never exceptions). The solver's answer is an immutable `{Param: value}` map;
  stale state is unrepresentable.
- **Local control vs solver control.** Anti-surge is an autonomous controller
  (`evaluate_with_surge_control`) applied inside every evaluation — invisible to the
  solver unless the solver explicitly varies that parameter, which *suspends* its
  controller for that solve.
- **The solver only ever solves 1D.** Bracket + brenth + typed endpoint failures.
  Multi-parameter modes are `CoupledParameter`s; multi-target is sections + the
  binding-section rule.
- **Fallbacks read as language:** `Constraint(vary=…, target=…, bounds=…,
  fallback=Constraint(…))` — pressure control is the *fallback* when speed
  saturates at its minimum.

## The four rings (one entry point: `solve`)

```
solve(system, constraints, feeds)
 └ constraint layer   fallback chains, binding-section rule (per section)
    └ numeric layer    bracketed 1D searches (brenth, capacity trimming)
       └ evaluation     controlled forward pass (anti-surge reflex inside)
```

`max_standard_rate` (capacity) is the inverse question — an outer 1D rate search
whose inner evaluation is the full `solve`.

## Module map

| Module | Contents |
|---|---|
| `params.py` | `Param` handle, `UNSET` sentinel |
| `units.py` | `Unit` types + `compute()`; `CompressorStage`, `Choke`, `Cooler`, `LiquidRemover`, `Splitter`, `Mixer`, `Shaft`, `CommonASVLoop`; `Ctx`/`Overrides` |
| `system.py` | `chain`, `ProcessSystem`, `State`, `CapacityViolation`, `evaluate` |
| `control.py` | `AntiSurgeController` (`evaluate_with_surge_control`) + the suspension rule |
| `solver/constraints.py` | `Bounds`/`FROM_CHART`/`FROM_CAPACITY`, `Probe`, `Target`, `Constraint` |
| `solver/numerics.py` | `find_root` (brenth), `binary_search_max`, capacity tolerance |
| `solver/result.py` | typed failures, `SolverResult` (`values` vs `auto_values`) |
| `solver/solver.py` | constraint solve, sections, binding-section rule |
| `solver/coupled.py` | `CoupledParameter` + balanced-rate/-pressure rules, equal-ratio |
| `solver/capacity.py` | `max_standard_rate` (the inverse question) |
| `display.py` | `display_topology` — the flat unit list for the frontend |

## Running the tests

```bash
uv run pytest tests/libecalc/process_concept_draft_v3 -q
uv run ruff check src/libecalc/process_concept_draft_v3
```
