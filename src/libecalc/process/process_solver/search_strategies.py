import abc
from collections.abc import Callable
from typing import NamedTuple

from scipy.optimize import root_scalar

from libecalc.common.errors.exceptions import EcalcError
from libecalc.process.process_solver.boundary import Boundary

CONVERGENCE_TOLERANCE = 1e-5


class BinarySearchResult(NamedTuple):
    search_higher: bool
    accepted: bool


ACCEPT_AND_GO_HIGHER = BinarySearchResult(search_higher=True, accepted=True)
ACCEPT_AND_GO_LOWER = BinarySearchResult(search_higher=False, accepted=True)
REJECT_AND_GO_HIGHER = BinarySearchResult(search_higher=True, accepted=False)
REJECT_AND_GO_LOWER = BinarySearchResult(search_higher=False, accepted=False)


def find_lowest_true(
    func: Callable[[float], bool],
    low: float,
    high: float,
    tolerance: float = CONVERGENCE_TOLERANCE,
    max_iterations: int = 30,
) -> float | None:
    if func(low):
        return low
    if not func(high):
        return None
    for _ in range(max_iterations):
        if (high - low) / max(abs(low), abs(high), 1.0) < tolerance:
            break
        mid = (low + high) / 2
        if func(mid):
            high = mid
        else:
            low = mid
    return high


def find_highest_true(
    func: Callable[[float], bool],
    low: float,
    high: float,
    tolerance: float = CONVERGENCE_TOLERANCE,
    max_iterations: int = 30,
) -> float | None:
    if func(high):
        return high
    if not func(low):
        return None
    for _ in range(max_iterations):
        if (high - low) / max(abs(low), abs(high), 1.0) < tolerance:
            break
        mid = (low + high) / 2
        if func(mid):
            low = mid
        else:
            high = mid
    return low


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


class SearchStrategy(abc.ABC):
    @abc.abstractmethod
    def search(self, boundary: Boundary, func: Callable[[float], BinarySearchResult]) -> float: ...


class BinarySearchStrategy(SearchStrategy):
    def __init__(self, tolerance: float = CONVERGENCE_TOLERANCE, max_iterations: int = 20):
        """

        Args:
            tolerance: The tolerance of convergence that will be used to exist the iteration
            max_iterations: The maximum number of iterations that will be used to find the root.
        """
        self._tolerance = tolerance
        self._max_iterations = max_iterations

    def search(self, boundary: Boundary, func: Callable[[float], BinarySearchResult]) -> float:
        """Binary search until we reach the maximum x value constrained by x_min and x_max
        where we have a search decision function.

        max(x) given f(x) == True

        We assume f(x) to be a binary (Heaviside step) function where f(x) is 1 for x <= n and 0 for x > n.
        n is the target value in this optimization. x == n is the highest possible value of x before f(x) turns to 0.

        The search function returns a BinarySearchResult. ``search_higher`` selects the next half interval,
        and ``accepted`` controls whether the convergence metric can be updated from that point.

        Note: This requires that the boolean condition is an indicator function where x > threshold returns False.
        """
        x0, x1 = boundary.min, boundary.max
        x2 = (x0 + x1) / 2  # Initial value x2.
        i = 0
        rel_diff = 100.0

        while (abs(rel_diff) > self._tolerance) and (i < self._max_iterations):
            x2 = (x0 + x1) / 2  # Bisecting x0 and x1.
            result = func(x2)
            if result.search_higher:
                x0, x1 = x2, x1  # x2 is valid. We can now search to the right in the binary three.
            else:
                x0, x1 = x0, x2  # x2 is invalid. We can now search to the left in the binary three

            if result.accepted:
                # Avoid division by zero: https://en.wikipedia.org/wiki/Relative_change_and_difference
                rel_diff = 0 if x0 == x1 else abs(x1 - x0) / max(abs(x0), abs(x1))
            i += 1

        if i >= self._max_iterations:
            raise DidNotConvergeError(
                boundary=boundary,
                tolerance=self._tolerance,
                iterations=self._max_iterations,
            )
        return x2


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
