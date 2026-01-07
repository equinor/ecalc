from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.domain.component_validation_error import ProcessPressureRatioValidationException
from libecalc.presentation.yaml.domain.expression_time_series_pressure import (
    ExpressionTimeSeriesPressure,
    InvalidPressureException,
)
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.mappers.consumer_function_mapper import validate_increasing_pressure

periods = [
    Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1)),
    Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1)),
    Period(start=datetime(2022, 1, 1), end=datetime(2023, 1, 1)),
]


def test_expression_with_negative_pressure(expression_evaluator_factory):
    evaluator = expression_evaluator_factory.from_periods(periods=periods, variables={"SIM1;PS": [10, -1, 20]})
    with pytest.raises(InvalidPressureException):
        ExpressionTimeSeriesPressure(
            time_series_expression=TimeSeriesExpression(expression="SIM1;PS", expression_evaluator=evaluator)
        )


def test_expression_where_sum_of_variables_give_negative_pressure(expression_evaluator_factory):
    evaluator = expression_evaluator_factory.from_periods(
        periods=periods, variables={"SIM1;PS": [10, 15, 20], "SIM2;PS": [8, 16, 18]}
    )
    with pytest.raises(InvalidPressureException):
        ExpressionTimeSeriesPressure(
            time_series_expression=TimeSeriesExpression(
                expression="SIM1;PS {-} SIM2;PS", expression_evaluator=evaluator
            )
        )


def test_expressions_with_pressure_ratio_less_than_one(expression_evaluator_factory):
    evaluator = expression_evaluator_factory.from_periods(
        periods=periods, variables={"SIM1;PS": [10, 15, 20], "SIM1;PMID": [10, 14, 20], "SIM1;PD": [15, 13, 20]}
    )

    with pytest.raises(ProcessPressureRatioValidationException):
        validate_increasing_pressure(
            suction_pressure=ExpressionTimeSeriesPressure(
                time_series_expression=TimeSeriesExpression(expression="SIM1;PS", expression_evaluator=evaluator)
            ),
            discharge_pressure=ExpressionTimeSeriesPressure(
                time_series_expression=TimeSeriesExpression(expression="SIM1;PD", expression_evaluator=evaluator)
            ),
        )

    with pytest.raises(ProcessPressureRatioValidationException):
        validate_increasing_pressure(
            suction_pressure=ExpressionTimeSeriesPressure(
                time_series_expression=TimeSeriesExpression(expression="SIM1;PS", expression_evaluator=evaluator)
            ),
            discharge_pressure=ExpressionTimeSeriesPressure(
                time_series_expression=TimeSeriesExpression(expression="SIM1;PD", expression_evaluator=evaluator)
            ),
            intermediate_pressure=ExpressionTimeSeriesPressure(
                time_series_expression=TimeSeriesExpression(expression="SIM1;PMID", expression_evaluator=evaluator)
            ),
        )
