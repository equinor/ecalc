"""NeqSim compatibility suite — pytest plugin hooks.

Two responsibilities:

* Auto-mark every test in the directory tree as ``neqsim_compat`` so
  the suite can be deselected from the default test run via
  ``pyproject.toml`` ``addopts``.
* Wire the ``--regenerate-neqsim-snapshot`` CLI flag that rebuilds
  the regression snapshot against the currently vendored NeqSim jar
  and exits without running tests.

Run the suite explicitly with::

    uv run pytest tests/ecalc_neqsim_wrapper/compatibility/

Regenerate the regression snapshot with::

    uv run pytest tests/ecalc_neqsim_wrapper/compatibility/ --regenerate-neqsim-snapshot
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REGEN_FLAG = "--regenerate-neqsim-snapshot"


def pytest_addoption(parser):
    parser.addoption(
        _REGEN_FLAG,
        action="store_true",
        default=False,
        help=(
            "Regenerate tests/ecalc_neqsim_wrapper/compatibility/regression/"
            "reference_snapshot.json against the currently vendored NeqSim "
            "jar, then exit without running any tests."
        ),
    )


def pytest_configure(config):
    # Explicit suite paths should not need `-m neqsim_compat`.
    if any("compatibility" in str(arg) for arg in config.args):
        config.option.markexpr = ""

    if config.getoption(_REGEN_FLAG):
        # Avoid loading NeqSim unless snapshot regeneration is requested.
        from .regression._regenerate import regenerate

        path = regenerate()
        pytest.exit(f"Regenerated NeqSim regression snapshot: {path}", returncode=0)


_SUITE_DIR = Path(__file__).parent


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    # Scope the marker to this suite; this hook can see repository tests.
    for item in items:
        try:
            item_path = Path(str(item.path))
        except (AttributeError, TypeError):
            continue
        if _SUITE_DIR in item_path.parents:
            item.add_marker(pytest.mark.neqsim_compat)
