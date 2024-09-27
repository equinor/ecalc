from datetime import date, datetime

import pytest

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.time_utils import Period, convert_date_to_datetime, default_temporal_model
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression


class TestConvertDateToDatetime:
    def test_date(self):
        assert convert_date_to_datetime(date(2020, 1, 1)) == datetime(2020, 1, 1, 0, 0, 0)

    def test_datetime(self):
        assert convert_date_to_datetime(datetime(2020, 1, 1, 12, 0, 0)) == datetime(2020, 1, 1, 12, 0, 0)


class TestDefaultDate:
    def test_none(self):
        assert default_temporal_model(None, default_period=Period(datetime.min)) is None

    def test_date_dict(self):
        date_data = {
            Period(datetime(2020, 12, 15), datetime(2021, 12, 15)): "EXPRESSION",
            Period(datetime(2021, 12, 15)): "2021",
        }
        assert default_temporal_model(date_data, default_period=Period(datetime.min)) == date_data

    def test_set_default(self):
        assert default_temporal_model("EXPRESSION", default_period=Period(datetime(1900, 1, 1))) == {
            Period(datetime(1900, 1, 1)): "EXPRESSION",
        }

    def test_invalid_date_dict(self):
        date_data = {
            Period(datetime(2020, 12, 15)): "EXPRESSION",
            "LOAD": "2021",
        }
        with pytest.raises(EcalcError) as e:
            default_temporal_model(date_data, default_period=Period(datetime.min))
        assert "Temporal models should only contain date keys" in str(e.value)
        assert "LOAD" in str(e.value)

    def test_date(self):
        """Test that date is converted to datetime."""
        expected = {Period(datetime(2019, 1, 1)): "EXPRESSION"}
        data = {Period(date(2019, 1, 1)): "EXPRESSION"}
        after = default_temporal_model(data, default_period=Period(datetime.min))
        assert after == expected


class TestConvertExpression:
    def test_none(self):
        assert convert_expression(None) is None

    def test_expression(self):
        assert convert_expression("SIM1;OIL_PROD {+} SIM1;GAS_PROD {/} 1000") == Expression.setup_from_expression(
            value="SIM1;OIL_PROD {+} SIM1;GAS_PROD {/} 1000"
        )

    def test_time_dependent_expression(self):
        assert convert_expression(
            {
                Period(datetime(2020, 12, 15), datetime(2021, 12, 15)): "SIM1;OIL_PROD {+} SIM1;GAS_PROD {/} 1000",
                Period(datetime(2021, 12, 15)): Expression.setup_from_expression(
                    value="SIM1;OIL_PROD {+} SIM1;GAS_PROD {/} 1000"
                ),
            }
        ) == {
            Period(datetime(2020, 12, 15), datetime(2021, 12, 15)): Expression.setup_from_expression(
                value="SIM1;OIL_PROD {+} SIM1;GAS_PROD {/} 1000"
            ),
            Period(datetime(2021, 12, 15)): Expression.setup_from_expression(
                value="SIM1;OIL_PROD {+} SIM1;GAS_PROD {/} 1000"
            ),
        }
