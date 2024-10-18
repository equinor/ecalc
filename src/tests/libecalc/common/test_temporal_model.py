from datetime import datetime

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.variables import VariablesMap
from libecalc.expression import Expression


class TestTemporalExpression:
    def test_single_value_expression(self):
        expression_evaluator = VariablesMap(
            time_vector=[
                datetime(2020, 1, 1),
                datetime(2021, 1, 1),
                datetime(2022, 1, 1),
                datetime(2022, 7, 1),
                datetime(2023, 1, 1),
            ]
        )
        assert expression_evaluator.evaluate(
            expression=TemporalModel({Period(datetime(2020, 1, 1)): Expression.setup_from_expression(1)}),
        ).tolist() == [1, 1, 1, 1]

    def test_single_value_expression_with_start_date_after_time_vector_start(self):
        expression_evaluator = VariablesMap(
            time_vector=[
                datetime(2019, 1, 1),
                datetime(2020, 1, 1),
                datetime(2021, 1, 1),
                datetime(2022, 7, 1),
                datetime(2023, 1, 1),
            ]
        )
        assert expression_evaluator.evaluate(
            expression=TemporalModel({Period(datetime(2020, 1, 1)): Expression.setup_from_expression(1)})
        ).tolist() == [0, 1, 1, 1]

    def test_multiple_times(self):
        expression_evaluator = VariablesMap(
            time_vector=[
                datetime(2019, 1, 1),
                datetime(2020, 1, 1),
                datetime(2021, 1, 1),
                datetime(2022, 1, 1),
                datetime(2022, 7, 1),
                datetime(2023, 1, 1),
            ]
        )
        assert expression_evaluator.evaluate(
            expression=TemporalModel(
                {
                    Period(datetime(2020, 1, 1), datetime(2022, 1, 1)): Expression.setup_from_expression(1),
                    Period(datetime(2022, 1, 1)): Expression.setup_from_expression(2),
                }
            )
        ).tolist() == [0, 1, 1, 2, 2]

    def test_multiple_times_with_references(self):
        expression_evaluator = VariablesMap(
            variables={"$var.var1": [5, 5, 5, 5, 5]},
            time_vector=[
                datetime(2019, 1, 1),
                datetime(2020, 1, 1),
                datetime(2021, 1, 1),
                datetime(2022, 1, 1),
                datetime(2022, 7, 1),
                datetime(2023, 1, 1),
            ],
        )

        assert expression_evaluator.evaluate(
            expression=TemporalModel(
                {
                    Period(datetime(2020, 1, 1), datetime(2022, 1, 1)): Expression.setup_from_expression(1),
                    Period(datetime(2022, 1, 1)): Expression.setup_from_expression("$var.var1"),
                }
            )
        ).tolist() == [0, 1, 1, 5, 5]
