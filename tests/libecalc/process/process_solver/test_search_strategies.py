"""Tests for Bisect."""

from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.search_strategies import Bisect


def test_search_returns_accepted_value():
    """Bisect.search should return a value that was accepted.

    The search converges to the boundary between accepted/rejected regions.
    The returned value must be from the accepted side, not an arbitrary midpoint
    that might be on the rejected side.
    """
    threshold = 0.1  # Chosen so the final midpoint lands on the invalid side

    def step_func(x: float) -> tuple[bool, bool]:
        if x < threshold:
            return True, True  # below threshold: go higher, accepted
        else:
            return False, True  # at/above threshold: go lower

    strategy = Bisect(tolerance=1e-5, max_iterations=50)
    result = strategy.search(boundary=Boundary(min=0.0, max=10.0), func=step_func)

    # The result must be below the threshold (on the accepted/valid side)
    assert result < threshold, (
        f"search() returned {result} which is >= threshold {threshold}. "
        f"It should return the last value from the accepted (higher=True) side."
    )
