"""Certified 1D search primitives — scipy only, no dependency on process_solver.

Two routines, two tolerances (mixing them up drifts parity):

- ``find_root`` wraps ``scipy.optimize.root_scalar(method="brenth")`` at root
  tolerance ``1e-5``; a non-converging or non-bracketing call raises
  ``DidNotConvergeError`` (scipy's ``ValueError`` for a non-sign-changing bracket
  is wrapped, matching the expected behavior).
- ``binary_search_max``: ``max(x)`` such
  that the boolean probe accepts, with the subtle accepted-only relative-diff
  convergence test. Capacity searches pass the coarser
  ``CAPACITY_SEARCH_TOLERANCE`` (1e-2) explicitly.
"""

from __future__ import annotations

from collections.abc import Callable

from scipy.optimize import root_scalar

ROOT_TOLERANCE = 1e-5
SEARCH_TOLERANCE = 1e-5
CAPACITY_SEARCH_TOLERANCE = 1e-2


class DidNotConvergeError(Exception):
    def __init__(self, lower: float, upper: float, tolerance: float, iterations: int):
        self.lower = lower
        self.upper = upper
        self.tolerance = tolerance
        self.iterations = iterations
        super().__init__(
            f"Did not converge after {iterations} iterations (bracket [{lower}, {upper}], tolerance {tolerance})."
        )


def find_root(
    lower: float,
    upper: float,
    func: Callable[[float], float],
    rtol: float = ROOT_TOLERANCE,
    max_iter: int = 50,
) -> float:
    """Bracketed root of ``func`` on ``[lower, upper]`` via brenth."""
    try:
        result = root_scalar(
            func,
            bracket=(lower, upper),
            maxiter=max_iter,
            method="brenth",
            rtol=rtol,
        )
    except ValueError as error:  # scipy raises when f(lower), f(upper) share a sign
        raise DidNotConvergeError(lower, upper, rtol, max_iter) from error
    if not result.converged:
        raise DidNotConvergeError(lower, upper, rtol, max_iter)
    return result.root


def binary_search_max(
    lower: float,
    upper: float,
    probe: Callable[[float], tuple[bool, bool]],
    tolerance: float = SEARCH_TOLERANCE,
    max_iter: int = 20,
) -> float:
    """Largest ``x`` whose probe ``(is_higher, is_accepted)`` accepts.

    Exact port of ``BinarySearchStrategy.search``: assumes a Heaviside boolean
    (accepts for ``x <= n``); the relative-difference convergence test updates
    only on accepted probes.
    """
    x0, x1 = lower, upper
    x2 = (x0 + x1) / 2
    last_accepted: float | None = None
    iteration = 0
    rel_diff = 100.0

    while abs(rel_diff) > tolerance and iteration < max_iter:
        x2 = (x0 + x1) / 2
        higher, accepted = probe(x2)
        if higher:
            x0, x1 = x2, x1
            if accepted:
                last_accepted = x2
        else:
            x0, x1 = x0, x2
        if accepted:
            rel_diff = 0 if x0 == x1 else abs(x1 - x0) / max(abs(x0), abs(x1))
        iteration += 1

    if iteration >= max_iter:
        raise DidNotConvergeError(lower, upper, tolerance, max_iter)
    return last_accepted if last_accepted is not None else x2
