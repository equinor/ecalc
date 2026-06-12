import abc
from collections.abc import Callable
from typing import NamedTuple

from scipy.optimize import root_scalar

from libecalc.common.errors.exceptions import EcalcError
from libecalc.process.process_solver.boundary import Boundary

CONVERGENCE_TOLERANCE = 1e-5


class BisectResult(NamedTuple):
    higher: bool
    accepted: bool


class DidNotConvergeError(EcalcError):
    def __init__(
        self,
        boundary: Boundary,
        tolerance: float,
        iterations: int,
    ):
        super().__init__(
            title="No solution found",
            message=f"Did not reach convergence after maximum number of iterations: {iterations}."
            f" lower bound: {boundary.min}, upper bound: {boundary.max}, convergence_tolerance: {tolerance}.",
        )


class Bisect:
    """Bisection over a numeric range to locate a boolean threshold.

    The condition is assumed monotonic (a single True/False crossing). Probes are evaluated
    at the midpoint of a shrinking bracket until it is narrower than ``tolerance``.
    """

    def __init__(self, tolerance: float = CONVERGENCE_TOLERANCE, max_iterations: int = 20):
        """

        Args:
            tolerance: The relative bracket width at which the search stops.
            max_iterations: The maximum number of bisection steps.
        """
        self._tolerance = tolerance
        self._max_iterations = max_iterations

    def _bisect(
        self,
        boundary: Boundary,
        probe: Callable[[float], BisectResult],
    ) -> float | None:
        """Bisect [boundary.min, boundary.max]. Returns the last accepted x, or ``None``."""
        x0, x1 = boundary.min, boundary.max
        last_accepted: float | None = None
        for _ in range(self._max_iterations):
            x2 = (x0 + x1) / 2
            higher, accepted = probe(x2)
            if accepted:
                last_accepted = x2
            if higher:
                x0 = x2
            else:
                x1 = x2
            rel_diff = (x1 - x0) / max(abs(x0), abs(x1), 1.0)
            if rel_diff < self._tolerance:
                break
        return last_accepted

    def search(self, boundary: Boundary, func: Callable[[float], BisectResult]) -> float:
        """Highest x in ``boundary`` where the indicator holds (``max(x) given f(x) == True``).

        ``func`` returns a ``BisectResult`` so steering (``higher``) and validity (``accepted``)
        are decoupled: a probe can steer the search without being accepted as a solution.

        We assume f(x) to be a binary (Heaviside step) function where f(x) is 1 for x <= n and 0 for x > n.
        n is the target value in this optimization. x == n is the highest possible value of x before f(x) turns to 0.

        Raises ``DidNotConvergeError`` if no probe was ever accepted.
        """
        result = self._bisect(boundary=boundary, probe=func)
        if result is None:
            raise DidNotConvergeError(
                boundary=boundary,
                tolerance=self._tolerance,
                iterations=self._max_iterations,
            )
        return result

    def lowest_true(self, boundary: Boundary, predicate: Callable[[float], bool]) -> float | None:
        """Return the lowest x in ``boundary`` where ``predicate(x)`` is True, or ``None``."""
        return self._first_true(boundary, predicate, lowest=True)

    def highest_true(self, boundary: Boundary, predicate: Callable[[float], bool]) -> float | None:
        """Return the highest x in ``boundary`` where ``predicate(x)`` is True, or ``None``."""
        return self._first_true(boundary, predicate, lowest=False)

    def _first_true(
        self,
        boundary: Boundary,
        predicate: Callable[[float], bool],
        *,
        lowest: bool,
    ) -> float | None:
        """Locate the boundary x where ``predicate`` flips, searching from the near end.

        ``lowest=True`` searches up from ``boundary.min`` for the lowest passing x;
        ``lowest=False`` searches down from ``boundary.max`` for the highest passing x.
        """
        near, far = (boundary.min, boundary.max) if lowest else (boundary.max, boundary.min)
        if predicate(near):
            return near
        if not predicate(far):
            return None

        def probe(x: float) -> BisectResult:
            ok = predicate(x)
            return BisectResult(higher=ok != lowest, accepted=ok)

        result = self._bisect(boundary=boundary, probe=probe)
        return result if result is not None else far


class RootFindingStrategy(abc.ABC):
    @abc.abstractmethod
    def find_root(
        self,
        boundary: Boundary,
        func: Callable[[float], float],
    ) -> float: ...


class ScipyRootFindingStrategy(RootFindingStrategy):
    def __init__(self, tolerance: float = CONVERGENCE_TOLERANCE, max_iterations: int = 50):
        """

        Args:
            tolerance: The tolerance of convergence that will be used to exist the iteration
            max_iterations: The maximum number of iterations that will be used to find the root.
        """
        # TODO: Investigate why we don't usE brentq method recommended by scipy
        self._tolerance = tolerance
        self._max_iterations = max_iterations

    def find_root(
        self,
        boundary: Boundary,
        func: Callable[[float], float],
    ) -> float:
        """Root finding using scipy´s implementation of the brenth method.

        This will try to solve for the root: f(x) = 0. Another way to say this is "what x makes the function return 0"...

        The result is bound on the interval [x0, x1].

        brenth is a version of Brent´s method (https://en.wikipedia.org/wiki/Brent%27s_method) with hyperbolic extrapolation

        :param boundary: Lower and upper of solution. Used as initial guess
        :param func: The function to be used in the secant root-finding method that we will solve f(x) = 0
        """
        result = root_scalar(
            func,
            bracket=(boundary.min, boundary.max),
            x0=boundary.min,
            x1=boundary.max,
            maxiter=self._max_iterations,
            method="brenth",
            rtol=self._tolerance,
        )
        if not result.converged:
            raise DidNotConvergeError(
                boundary=boundary,
                tolerance=self._tolerance,
                iterations=self._max_iterations,
            )
        return result.root
