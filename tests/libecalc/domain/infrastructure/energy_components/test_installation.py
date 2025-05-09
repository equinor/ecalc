from datetime import datetime

import pytest
from libecalc.common.time_utils import Period
from libecalc.common.variables import VariablesMap
from libecalc.domain.component_validation_error import ComponentValidationException
from libecalc.expression import Expression
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation


def test_valid_regularity():
    # Test that a valid regularity value (between 0 and 1) does not raise any exceptions
    # during the initialization of the Installation instance.

    period = Period(datetime(2023, 1, 1), datetime(2024, 1, 1))
    regularity = {period: Expression.setup_from_expression(0.5)}
    hydrocarbon_export = {period: Expression.setup_from_expression(100)}
    expression_evaluator = VariablesMap(time_vector=[period.start, period.end])

    # Create Installation instance
    Installation(
        name="Test Installation",
        regularity=regularity,
        hydrocarbon_export=hydrocarbon_export,
        fuel_consumers=[],
        expression_evaluator=expression_evaluator,
    )


def test_invalid_regularity():
    # Test that an invalid regularity value (outside the range 0 to 1) raises a
    # ComponentValidationException with the correct error message.

    period1 = Period(datetime(2023, 1, 1), datetime(2024, 1, 1))
    period2 = Period(datetime(2024, 1, 1), datetime(2025, 1, 1))

    regularity = {
        period1: Expression.setup_from_expression(0.5),
        period2: Expression.setup_from_expression(10),  # Invalid value
    }
    hydrocarbon_export = {
        period1: Expression.setup_from_expression(100),
        period2: Expression.setup_from_expression(200),
    }
    expression_evaluator = VariablesMap(time_vector=[period1.start, period2.start, period2.end])

    # Expect a ComponentValidationException for invalid regularity
    with pytest.raises(ComponentValidationException) as excinfo:
        Installation(
            name="Test Installation",
            regularity=regularity,
            hydrocarbon_export=hydrocarbon_export,
            fuel_consumers=[],
            expression_evaluator=expression_evaluator,
        )

    assert "REGULARITY must evaluate to a fraction between 0 and 1. Got: 10" in str(excinfo.value)
