from datetime import datetime

from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.variables import VariablesMap
from libecalc.expression import Expression


class TestTemporalExpression:
    def test_single_value_expression(self):
        assert TemporalExpression.evaluate(
            temporal_expression=TemporalModel({datetime(2020, 1, 1): Expression.setup_from_expression(1)}),
            variables_map=VariablesMap(
                global_time_vector=[
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                    datetime(2022, 7, 1),
                    datetime(2023, 7, 1),
                ]
            ),
        ) == [1, 1, 1, 1]

    def test_single_value_expression_with_start_date_after_time_vector_start(self):
        assert TemporalExpression.evaluate(
            temporal_expression=TemporalModel({datetime(2020, 1, 1): Expression.setup_from_expression(1)}),
            variables_map=VariablesMap(
                global_time_vector=[
                    datetime(2019, 1, 1),
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                    datetime(2022, 7, 1),
                    datetime(2023, 1, 1),
                ]
            ),
        ) == [0, 1, 1, 1]

    def test_multiple_times(self):
        assert TemporalExpression.evaluate(
            temporal_expression=TemporalModel(
                {
                    datetime(2020, 1, 1): Expression.setup_from_expression(1),
                    datetime(2022, 1, 1): Expression.setup_from_expression(2),
                }
            ),
            variables_map=VariablesMap(
                global_time_vector=[
                    datetime(2019, 1, 1),
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                    datetime(2022, 7, 1),
                    datetime(2023, 1, 1),
                ]
            ),
        ) == [0, 1, 1, 2, 2]

    def test_multiple_times_with_references(self):
        assert TemporalExpression.evaluate(
            temporal_expression=TemporalModel(
                {
                    datetime(2020, 1, 1): Expression.setup_from_expression(1),
                    datetime(2022, 1, 1): Expression.setup_from_expression("$var.var1"),
                }
            ),
            variables_map=VariablesMap(
                variables={"$var.var1": [5, 5, 5, 5, 5]},
                global_time_vector=[
                    datetime(2019, 1, 1),
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                    datetime(2022, 7, 1),
                    datetime(2023, 1, 1),
                ],
            ),
        ) == [0, 1, 1, 5, 5]
