from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.domain.regularity import InvalidRegularity, Regularity


def test_valid_regularity(expression_evaluator_factory):
    # Test that a valid regularity value (between 0 and 1) does not raise any exceptions
    # during the initialization of the Installation instance.
    period = Period(datetime(2023, 1, 1), datetime(2024, 1, 1))
    expression_evaluator = expression_evaluator_factory.from_time_vector(time_vector=[period.start, period.end])

    # Instance should be created successfully:
    Regularity(
        expression_evaluator=expression_evaluator, target_period=expression_evaluator.get_period(), expression_input=0.5
    )


def test_invalid_regularity(expression_evaluator_factory):
    # Test that an invalid regularity value (outside the range 0 to 1) raises a
    # ComponentValidationException with the correct error message.

    period1 = Period(datetime(2023, 1, 1), datetime(2024, 1, 1))
    period2 = Period(datetime(2024, 1, 1), datetime(2025, 1, 1))

    expressions = {
        period1.start: 0.5,
        period2.start: 10,  # Invalid value
    }

    expression_evaluator = expression_evaluator_factory.from_periods(periods=[period1, period2])

    # Expect a ComponentValidationException for invalid regularity
    with pytest.raises(InvalidRegularity) as excinfo:
        Regularity(
            expression_evaluator=expression_evaluator,
            expression_input=expressions,
            target_period=expression_evaluator.get_period(),
        )
    assert ("REGULARITY must evaluate to fractions between 0 and 1. Invalid values: [10.0]") in str(excinfo.value)
