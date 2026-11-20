# AGENTS.md

This directory (`libecalc/`) is a separate git repository containing the core domain library and CLI.

## Test Commands

Run from `libecalc/`:

```sh
python -m pytest                                    # Run all tests
python -m pytest path/to/test_file.py               # Single test file
python -m pytest path/to/test_file.py::test_func     # Single test function
```

Always exclude the `dockersnapshot` and `x86` markers when running locally — these tests require an x86 container
(snapshot generation) and will fail or be skipped-in-spirit on other architectures (e.g. Apple Silicon):

```sh
python -m pytest -m "not dockersnapshot and not x86"
```

Other markers (see `pyproject.toml`): `e2e`, `integtest`, `slow`, `snapshot`, `inlinesnapshot`, `arch`.

## Code Style

- **Python 3.12+**, package manager **uv**.
- **Ruff** for linting/formatting: line length 120.
- Type hints required throughout; modern syntax (`str | None`, `list[str]`, not `Optional`/`List`).
- Don't add comments or docstrings unless explicitly asked; prefer self-documenting code.

## Validation

- Validate in the domain model (`src/libecalc/ecalc_model`), not in the YAML types. Prefer this over pydantic
  validators in `presentation/yaml/yaml_types`, which should only check the shape of the input.
- It must not be possible to instantiate an invalid domain object: entities validate in `__init__` before assigning
  state, value objects (`@value_object`) validate in `__post_init__`. There is no separate `validate()` step.
- Check invariants an object can see on its own (e.g. pump chart efficiency, sequential periods, rate fractions
  between 0 and 1). Check rules across children in their owner (e.g. `PumpSimulation` checks one stream per pump
  problem and the outlet pressure in periods where the pump runs). Rules across aggregates that are only referenced
  by id belong in the mapper or a domain service.
- Raise `InvalidEcalcModelException` from `libecalc.ecalc_model.validation` (an `EcalcValidationException`, so the
  YAML model reports it as a model validation error). Reuse the `require_*` helpers there, and give messages that
  name the object, the value and the period.
- Add a test for every rule that checks the object cannot be created.

