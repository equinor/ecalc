from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.optimize import root_scalar

from libecalc.common.logger import logger

# Constants
CONVERGENCE_TOLERANCE = 1e-5
MAXIMUM_NUMBER_OF_ITERATIONS = 50

# Adaptive damping defaults
EPSILON_LARGE = 0.01  # relative step (>X relative change to value is considered "large" enough to trigger damping)
OSCILL_FLIP_REQ = 2  # number of flips before damping (combined with large step)
STEP_DOWN = 0.5  # factor to reduce beta
STEP_UP = 1.5  # factor to increase beta
BETA_MIN = 0.10  # minimum beta
BETA_MAX = 1.00  # maximum beta
STABLE_ITERS = 3  # number of stable iterations before increasing beta


@dataclass
class DampState:
    """Holds state for adaptive under‑relaxation across iterations."""

    beta: float = 1.0
    delta_prev: float | None = None
    flip_counter: int = 0
    stable_counter: int = 0


def adaptive_pressure_update(*, p_prev: float, p_raw: float, state: DampState) -> tuple[float, DampState]:
    """
    Return damped pressure and update state.

    Damping engages when the update flips sign twice and new P remains larger
    than EPS_LARGE * p_prev. Once the iteration becomes monotone small for
    STABLE_ITERS successive steps, beta is relaxed toward 1 again.
    """

    delta = p_raw - p_prev
    large_step = abs(delta) > EPSILON_LARGE * p_prev
    flip = state.delta_prev is not None and (delta * state.delta_prev) < 0.0

    # Oscillation detection
    if flip and large_step:
        state.flip_counter += 1
    else:
        state.flip_counter = 0

    # Beta adaptation
    if state.flip_counter >= OSCILL_FLIP_REQ:
        logger.debug(f"Adaptive damping engaged. p_prev: {p_prev}, p_raw: {p_raw}, delta: {delta}, beta: {state.beta}")
        state.beta = max(BETA_MIN, state.beta * STEP_DOWN)
        state.stable_counter = 0
    else:
        state.stable_counter += 1
        if state.stable_counter >= STABLE_ITERS:
            logger.debug(
                f"Adaptive damping relaxed. p_prev: {p_prev}, p_raw: {p_raw}, delta: {delta}, beta: {state.beta}"
            )
            state.beta = min(BETA_MAX, state.beta * STEP_UP)
            state.stable_counter = 0

    p_next = p_prev + state.beta * delta
    state.delta_prev = delta
    return p_next, state


def find_root(
    lower_bound: float,
    upper_bound: float,
    func: Callable,
    relative_convergence_tolerance: float = CONVERGENCE_TOLERANCE,
    maximum_number_of_iterations: int = MAXIMUM_NUMBER_OF_ITERATIONS,
) -> float:
    """Root finding using scipy´s implementation of the brenth method.

    TODO: Investigate why we don't use brentq method recommended by scipy

    This will try to solve for the root: f(x) = 0. Another way to say this is "what x makes the function return 0"...

    The result is bound on the interval [x0, x1].

    brenth is a version of Brent´s method (https://en.wikipedia.org/wiki/Brent%27s_method) with hyperbolic extrapolation

    :param lower_bound: Lower bound of solution. Used as initial guess
    :param upper_bound: Upper bound of solution. Used as second guess
    :param func: The function to be used in the secant root-finding method that we will solve f(x) = 0
    :param relative_convergence_tolerance: The tolerance of convergence that will be used to exist the iteration
    :param maximum_number_of_iterations: The maximum number of iterations that will be used to find the root.
    """
    try:
        result = root_scalar(
            func,
            bracket=(lower_bound, upper_bound),
            x0=lower_bound,
            x1=upper_bound,
            maxiter=maximum_number_of_iterations,
            method="brenth",
            rtol=relative_convergence_tolerance,
        )
        if not result.converged:
            msg = (
                f"Did not reach convergence after maximum number of iterations: {maximum_number_of_iterations}."
                f" root given last iteration: {result.root}, convergence_tolerance: {relative_convergence_tolerance}."
                f" on interval [{lower_bound},{upper_bound}]."
                f" func: {func}"
            )
            logger.error(msg)
        return result.root
    except Exception as e:
        logger.error(
            f"Failed to find roots using Brent's method. Please report to the eCalc team."
            f" Bound to the interval [{lower_bound}, {upper_bound}], function: {func}"
            f" Max iterations: {maximum_number_of_iterations}, convergence_tolerance: {relative_convergence_tolerance}."
            f" Fallback to secant method bounded on the interval [{lower_bound}, {upper_bound}]. " + str(e)
        )
    return secant_method(
        x0=lower_bound,
        x1=upper_bound,
        func=func,
        convergence_tolerance=relative_convergence_tolerance,
        maximum_number_of_iterations=maximum_number_of_iterations,
    )


def secant_method(
    x0: float,
    x1: float,
    func: Callable,
    convergence_tolerance: float = CONVERGENCE_TOLERANCE,
    maximum_number_of_iterations: int = MAXIMUM_NUMBER_OF_ITERATIONS,
    bounded_to_input_x_interval: bool = True,
) -> float:
    """Keeping for now as fallback for root finding method above.

    Root finding using the Secant method.

    since we want to find the x that solves for the root: f(x) = 0. bound to the interval [x0, x1]
    Ref. https://en.wikipedia.org/wiki/Secant_method.
    :param x0: Starting-point for iteration together with x1
    :param x1: Starting-point for iteration together with x0
    :param func: The function to be used in the secant root-finding method that we will solve f(x) = 0
    :param convergence_tolerance: The tolerance of convergence that will be used to exist the iteration
    :param maximum_number_of_iterations: The maximum number of iterations that will be used to find the root.
    :param bounded_to_input_x_interval: Whether to search outside the input interval [x0, x1] for roots.
    """
    f = func
    minimum_x_value = min(x0, x1)
    maximum_x_value = max(x0, x1)

    def limit_to_bounds(x: int | float, x_min: int | float, x_max: int | float) -> int | float:
        return max(min(x, x_max), x_min) if bounded_to_input_x_interval else x

    x2 = np.nan  # Dummy value before iteration
    i = 0
    f0 = 0
    f1 = 1

    rel_diff = 100.0
    # Loop until we reach the target tolerance or max iterations.
    while (abs(rel_diff) > convergence_tolerance) and (i <= maximum_number_of_iterations) and (f1 != f0):
        f0 = f(x0)
        f1 = f(x1)
        x2 = x1 - f1 * (x1 - x0) / float(f1 - f0)
        x2 = limit_to_bounds(x2, minimum_x_value, maximum_x_value)
        x0, x1 = x1, x2  # Update indexes for next iteration
        i += 1
        # Avoid division by zero: https://en.wikipedia.org/wiki/Relative_change_and_difference
        rel_diff = 0 if x0 == x1 else abs(x1 - x0) / max(abs(x0), abs(x1))

    if i > maximum_number_of_iterations:
        msg = (
            f"Did not reach convergence after maximum number of iterations: {maximum_number_of_iterations}."
            f" x0: {x0}, x1: {x1}, convergence_tolerance: {convergence_tolerance}."
            f" bounded to input interval: {bounded_to_input_x_interval}"
            f" on interval [{minimum_x_value},{maximum_x_value}]."
            f" func: {func}"
        )
        logger.error(msg)
    return x2


def maximize_x_given_boolean_condition_function(
    x_min: float,
    x_max: float,
    bool_func: Callable,
    convergence_tolerance: float = CONVERGENCE_TOLERANCE,
    maximum_number_of_iterations: int = MAXIMUM_NUMBER_OF_ITERATIONS,
) -> float:
    """Binary search until we reach the maximum x value constrained by x_min and x_max
    where we have a boolean constraint condition given as a function.

    max(x) given f(x) == True

    We assume f(x) to be a binary (Heaviside step) function where f(x) is 1 for x <= n and 0 for x > n.
    n is the target value in this optimization. x == n is the highest possible value of x before f(x) turns to 0.

    Note: This requires that the boolean condition is an indicator function where x > threshold returns False.
    """
    x0, x1 = x_min, x_max
    x2 = (x0 + x1) / 2  # Initial value x2.
    i = 0
    rel_diff = 100.0

    while (abs(rel_diff) > convergence_tolerance) and (i <= maximum_number_of_iterations):
        x2 = (x0 + x1) / 2  # Bisecting x0 and x1.
        if bool_func(x2):
            x0, x1 = x2, x1  # x2 is valid. We can now search to the right in the binary three.
            # Avoid division by zero: https://en.wikipedia.org/wiki/Relative_change_and_difference
            rel_diff = 0 if x0 == x1 else abs(x1 - x0) / max(abs(x0), abs(x1))
        else:
            x0, x1 = x0, x2  # x2 is invalid. We can now search to the left in the binary three
            # rel_diff does not change since the solution is not valid. Otherwise we could accept a non-True solution.
        i += 1

    if i > maximum_number_of_iterations:
        msg = (
            f"Did not reach convergence after maximum number of iterations: {maximum_number_of_iterations}."
            f" x_min: {x_min}, x_max: {x_max}, convergence_tolerance: {convergence_tolerance}."
            f" bool_func: {bool_func}"
        )
        logger.error(msg)
    return x2
