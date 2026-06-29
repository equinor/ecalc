"""Numerics: certified 1D search primitives (ported from test_search_strategies)."""

from __future__ import annotations

import math

import pytest

from libecalc.process_concept_draft_v3.solver.numerics import (
    CAPACITY_SEARCH_TOLERANCE,
    DidNotConvergeError,
    binary_search_max,
    find_root,
)


def test_binary_search_returns_accepted_value():
    threshold = 0.1

    def step(x: float) -> tuple[bool, bool]:
        if x < threshold:
            return True, True
        return False, True

    result = binary_search_max(0.0, 10.0, step, tolerance=1e-5, max_iter=50)
    assert result < threshold


def test_binary_search_only_accepts_feasible_probes():
    """Unaccepted highs must never be returned even if they are 'higher'."""
    threshold = 5.0

    def probe(x: float) -> tuple[bool, bool]:
        if x < threshold:
            return True, True  # feasible, go higher
        return False, False  # infeasible (e.g. RateTooHigh), not accepted

    result = binary_search_max(0.0, 10.0, probe, tolerance=CAPACITY_SEARCH_TOLERANCE)
    assert result < threshold


def test_binary_search_iteration_cap_raises():
    def never_converges(x: float) -> tuple[bool, bool]:
        # Always "higher and accepted" but never narrows enough at tiny tolerance.
        return True, True

    # max(x) keeps moving toward upper; with a very tight tolerance and few iters it caps.
    with pytest.raises(DidNotConvergeError):
        binary_search_max(0.0, 1e9, never_converges, tolerance=1e-12, max_iter=3)


def test_find_root_finds_bracketed_root():
    root = find_root(0.0, 10.0, lambda x: x - 3.0)
    assert root == pytest.approx(3.0, abs=1e-4)


def test_find_root_nonlinear():
    root = find_root(0.0, 2.0, lambda x: math.exp(x) - 2.0)
    assert root == pytest.approx(math.log(2.0), abs=1e-4)


def test_find_root_no_sign_change_raises_did_not_converge():
    with pytest.raises(DidNotConvergeError):
        find_root(1.0, 2.0, lambda x: x + 5.0)  # no root in bracket; scipy ValueError wrapped
