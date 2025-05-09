import pytest

from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    DampState,
    adaptive_pressure_update,
    find_root,
    maximize_x_given_boolean_condition_function,
    secant_method,
)


def func(x):
    return x**3 - 4  # only one real root at x = 1.58740


def func_prime(x):
    return 3 * x**2 - 2


def func_quadratic(x):
    return (x - 2) * x * (x + 2) ** 2 + 2


def func_bool(x):
    return x < 5


def inverse_func_bool(x):
    return x > 5


def invalid_bool_func(x):
    return False


def test_root_finding_method_func():
    result_scipy = find_root(lower_bound=0, upper_bound=10, func=func)
    result_custom = secant_method(x0=0, x1=10, func=func)
    assert result_scipy == pytest.approx(1.58740, rel=0.01)
    assert result_scipy == pytest.approx(result_custom, rel=0.01)


def test_root_finding_method_func_prime():
    result_scipy = find_root(lower_bound=0, upper_bound=10, func=func_prime)
    result_custom = secant_method(x0=0, x1=10, func=func_prime)
    assert result_scipy == pytest.approx(0.81649, rel=0.01)
    assert result_scipy == pytest.approx(result_custom, rel=0.01)


def test_root_finding_method_func_quadratic():
    result_scipy = find_root(lower_bound=0, upper_bound=10, func=func_quadratic)
    result_custom = secant_method(x0=0, x1=10, func=func_quadratic)
    assert result_scipy == pytest.approx(0, rel=0.01)
    assert result_scipy == pytest.approx(result_custom, rel=0.01)


@pytest.mark.skip("deactivate caplog tests for now")
def test_root_finding_solution_out_of_bounds(caplog):
    """SciPy's standard Brent method does not throw exceptions for solutions outside bounds. Check that error is logged when solution is out of bounds."""
    find_root(lower_bound=1, upper_bound=2, func=lambda x: x**2)
    assert "Failed to find roots" in caplog.text


def test_maximize_x_given_boolean_condition_function():
    """This is not True in x_min, nor (x_min + x_max) / 2. So it will converge towards x_min with a warning."""
    result = maximize_x_given_boolean_condition_function(x_min=0, x_max=10, bool_func=inverse_func_bool)
    assert result == pytest.approx(0, rel=0.01)


def test_maximize_x_given_strange_boolean_condition_function():
    """This will return True at x_max and False at x_min. Since x_max is the highest possible value, we will return x_max."""
    result = maximize_x_given_boolean_condition_function(x_min=0, x_max=10, bool_func=func_bool)
    assert result == pytest.approx(5, rel=0.01)


def test_maximize_x_given_invalid_boolean_condition_function():
    """This function is invalid since it will always return False. However, it has been decided that we do not want to
    crash the program, so we rather log an error to the user.
    """
    result = maximize_x_given_boolean_condition_function(x_min=0, x_max=10, bool_func=invalid_bool_func)
    assert result == pytest.approx(0, rel=0.01)


def test_adaptive_pressure_update_beta_reduces_after_two_large_flips():
    """
    After two sign flips with large amplitude β must be < 1 (damped).
    """

    state = DampState()
    p_prev = 100.0

    # 1st step – no previous delta → β remains 1
    p_next, state = adaptive_pressure_update(p_prev=p_prev, p_raw=300.0, state=state)
    assert state.beta == 1.0

    # 2nd step – first flip
    p_next, state = adaptive_pressure_update(p_prev=p_next, p_raw=50.0, state=state)
    assert state.beta == 1.0, "β should not change on first flip"

    # 3rd step – second flip with large amplitude → damping engaged
    p_next, state = adaptive_pressure_update(p_prev=p_next, p_raw=300.0, state=state)
    assert state.beta < 1.0, "β was not reduced after two large flips"


def test_adaptive_pressure_update_beta_recovers_after_stable_iterations():
    """
    Once the iteration is monotone small for a few steps β should climb back.
    """

    state = DampState(beta=0.3)  # start from a damped value
    p_prev = 100.0

    # give three small, same‑sign corrections
    for _ in range(3):
        p_prev, state = adaptive_pressure_update(p_prev=p_prev, p_raw=p_prev * 1.01, state=state)

    assert state.beta > 0.3, "β did not relax upward after several stable small steps"
