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

