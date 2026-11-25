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

## Legacy Code

The following paths are legacy. Do not read them for context, copy patterns, naming or structure from them, import
from them in new code, or modify them unless explicitly asked. New code and structure must follow the non-legacy
modules only.

Paths under `src/`:

- `src/ecalc_cli/`

Paths under `src/libecalc/`:

- `application/`
- `domain/`, except the top-level files prefixed with `time_series_`
- `dto/`
- `examples/`, except where new code is used
- `fixtures/`, except `fixtures/cases/nextgen/`
- `presentation/exporter/`
- `presentation/flow_diagram/`
- `presentation/json_result/`
- `presentation/simple_result/`

## Code Style

- **Python 3.12+**, package manager **uv**.
- **Ruff** for linting/formatting: line length 120.
- Type hints required throughout; modern syntax (`str | None`, `list[str]`, not `Optional`/`List`).
- Don't add comments or docstrings unless explicitly asked; prefer self-documenting code.

