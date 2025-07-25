from datetime import datetime
from typing import Literal

import pydantic
import pytest
from inline_snapshot import snapshot
from pydantic import TypeAdapter

from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.dto.types import InterpolationType
from libecalc.presentation.yaml.domain.time_series_collection import TimeSeriesCollection
from libecalc.presentation.yaml.domain.time_series_resource import (
    InvalidTimeSeriesResourceException,
    TimeSeriesResource,
)
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection


def _create_timeseries_data(
    typ: Literal["MISCELLANEOUS", "DEFAULT"],
    name: str,
    file: str,
    influence_time_vector: bool | None = None,
    extrapolate_outside: bool | None = None,
    interpolation_type: InterpolationType | None = None,
) -> dict:
    timeseries_dict = {
        EcalcYamlKeywords.type: typ,
        EcalcYamlKeywords.name: name,
        EcalcYamlKeywords.file: file,
    }

    if influence_time_vector is not None:
        timeseries_dict[EcalcYamlKeywords.time_series_influence_time_vector] = influence_time_vector

    if extrapolate_outside is not None:
        timeseries_dict[EcalcYamlKeywords.time_series_extrapolate_outside_defined] = extrapolate_outside

    if interpolation_type is not None:
        timeseries_dict[EcalcYamlKeywords.time_series_interpolation_type] = interpolation_type.value

    return timeseries_dict


class TestTimeSeries:
    parameterized_valid_timeseries_data = [
        (
            "MISCELLANEOUS",
            True,
            True,
            InterpolationType.LEFT,
            True,
        )
    ]

    @pytest.mark.parametrize(
        "typ_enum, extrapolate, influence_time_vector, interpolation_type, extrapolate_result",
        parameterized_valid_timeseries_data,
    )
    def test_valid_minimal_timeseries_different_types(
        self,
        typ_enum,
        extrapolate,
        influence_time_vector,
        interpolation_type,
        extrapolate_result,
    ):
        filename = "test.csv"
        resource = TimeSeriesResource(MemoryResource(headers=["DATE", "OIL_PROD"], data=[["01.01.2017"], [5016]]))

        timeseries_model = TimeSeriesCollection.from_yaml(
            resource=resource,
            yaml_collection=TypeAdapter(YamlTimeSeriesCollection).validate_python(
                _create_timeseries_data(
                    typ=typ_enum,
                    name="SIM1",
                    file=filename,
                    extrapolate_outside=extrapolate,
                    interpolation_type=interpolation_type,
                    influence_time_vector=influence_time_vector,
                )
            ),
        )

        assert timeseries_model.name == "SIM1"
        assert timeseries_model.get_time_series_references() == ["OIL_PROD"]
        assert timeseries_model.get_time_vector() == [datetime(2017, 1, 1)]
        assert timeseries_model.should_influence_time_vector() is True

        time_series = timeseries_model.get_time_series("OIL_PROD")
        assert time_series.series == [5016]
        assert time_series.time_vector == [datetime(2017, 1, 1)]
        assert time_series._extrapolate is extrapolate_result
        assert timeseries_model._interpolation == InterpolationType.LEFT

    def test_valid_time_series_multiple_columns(self):
        """
        Test TimeSeriesCollection.type 'DEFAULT' defaults
        """
        filename = "test_multiple_columns.csv"
        resource = TimeSeriesResource(
            MemoryResource(
                headers=["DATE", "COLUMN1", "COLUMN2", "COLUMN3"],
                data=[["01.01.2015", "01.01.2016"], [1, 2], [3, 4], [5, 6]],
            )
        )

        timeseries_model = TimeSeriesCollection.from_yaml(
            resource=resource,
            yaml_collection=TypeAdapter(YamlTimeSeriesCollection).validate_python(
                _create_timeseries_data(
                    typ="DEFAULT",
                    name="SIM1",
                    file=filename,
                    extrapolate_outside=None,
                    interpolation_type=None,
                    influence_time_vector=True,
                )
            ),
        )

        assert timeseries_model.name == "SIM1"
        assert timeseries_model.get_time_series_references() == ["COLUMN1", "COLUMN2", "COLUMN3"]
        assert timeseries_model.get_time_vector() == [datetime(2015, 1, 1), datetime(2016, 1, 1)]
        assert timeseries_model.should_influence_time_vector() is True

        time_series = timeseries_model.get_time_series("COLUMN1")
        assert time_series.series == [1, 2]
        assert time_series.time_vector == [datetime(2015, 1, 1), datetime(2016, 1, 1)]
        assert time_series._extrapolate is False
        assert timeseries_model._interpolation == InterpolationType.RIGHT

        time_series = timeseries_model.get_time_series("COLUMN2")
        assert time_series.series == [3, 4]
        assert time_series.time_vector == [datetime(2015, 1, 1), datetime(2016, 1, 1)]
        assert time_series._extrapolate is False
        assert timeseries_model._interpolation == InterpolationType.RIGHT

        time_series = timeseries_model.get_time_series("COLUMN3")
        assert time_series.series == [5, 6]
        assert time_series.time_vector == [datetime(2015, 1, 1), datetime(2016, 1, 1)]
        assert time_series._extrapolate is False
        assert timeseries_model._interpolation == InterpolationType.RIGHT

    def test_valid_time_series_unsorted(self):
        filename = "test_unsorted.csv"
        resource = TimeSeriesResource(
            MemoryResource(
                headers=["DATE", "COLUMN1", "COLUMN2"],
                data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, 3], [2, 3, 1]],
            )
        )

        timeseries_model = TimeSeriesCollection.from_yaml(
            resource=resource,
            yaml_collection=TypeAdapter(YamlTimeSeriesCollection).validate_python(
                _create_timeseries_data(
                    typ="DEFAULT",
                    name="SIM1",
                    file=filename,
                    extrapolate_outside=None,
                    influence_time_vector=True,
                    interpolation_type=None,
                )
            ),
        )

        assert timeseries_model.name == "SIM1"
        assert timeseries_model.get_time_series_references() == ["COLUMN1", "COLUMN2"]
        assert timeseries_model.get_time_vector() == [datetime(2015, 1, 1), datetime(2016, 1, 1), datetime(1900, 1, 1)]
        assert timeseries_model.should_influence_time_vector() is True

        time_series = timeseries_model.get_time_series("COLUMN1")
        assert time_series.series == [3, 1, 2]
        assert time_series.time_vector == [datetime(1900, 1, 1), datetime(2015, 1, 1), datetime(2016, 1, 1)]

        time_series = timeseries_model.get_time_series("COLUMN2")
        assert time_series.series == [1, 2, 3]
        assert time_series.time_vector == [datetime(1900, 1, 1), datetime(2015, 1, 1), datetime(2016, 1, 1)]

    parameterized_invalid_timeseries_data = [
        # headers, data mismatch (+1)
        (
            ["DATE", "OIL_PROD", "BVBV"],
            [["01.01.2017"], [5016]],
            snapshot("Missing column: Column matching header 'BVBV' is missing."),
        ),
        # no data
        (
            ["DATE", "DUMMY"],
            [["01.01.2017"]],
            snapshot("Missing column: Column matching header 'DUMMY' is missing."),
        ),
        # no time
        (
            ["DATE", "OIL_PROD"],
            [[], [5016]],
            snapshot("Invalid time series resource: The time vector is empty"),
        ),
        # no headers
        (
            [],
            [["01.01.2017"], [5016]],
            snapshot("Invalid resource: Resource must at least have one column"),
        ),
        # mismatch data, time
        (
            ["DATE", "OIL_PROD"],
            [["01.01.2017", "01.01.2018"], [5016]],
            snapshot("Rows mismatch: The number of records for times and data do not match: data: 1, time_vector: 2"),
        ),
        # mismatch data, time
        (
            ["DATE", "OIL_PROD"],
            [["01.01.2017"], [5016, 5026]],
            snapshot("Rows mismatch: The number of records for times and data do not match: data: 2, time_vector: 1"),
        ),
        # no data cols
        (
            ["DATE", "HEADER"],
            [["01.01.2017"]],
            snapshot("Missing column: Column matching header 'HEADER' is missing."),
        ),
        # duplicate dates
        (
            ["DATE", "HEADER"],
            [["01.01.2015", "01.01.2016", "01.01.2017", "01.01.2017"], [5016, 5036, 5026, 5216]],
            snapshot(
                "Invalid time series resource: The time series resource contains duplicate dates: 2017-01-01 00:00:00"
            ),
        ),
        # string values
        (
            ["DATE", "HEADER"],
            [["01.01.2015", "01.01.2016", "01.01.2017"], [5016, 5036, "invalid"]],
            snapshot("Invalid column: The timeseries column 'HEADER' contains non-numeric values."),
        ),
    ]

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    @pytest.mark.parametrize(
        "headers, columns, error_message",
        parameterized_invalid_timeseries_data,
    )
    def test_invalid_timeseries(self, headers, columns, error_message):
        filename = "test.csv"

        with pytest.raises(InvalidResourceException) as ve:
            resource = TimeSeriesResource(MemoryResource(headers=headers, data=columns)).validate()
            TimeSeriesCollection.from_yaml(
                resource=resource,
                yaml_collection=TypeAdapter(YamlTimeSeriesCollection).validate_python(
                    _create_timeseries_data(
                        typ="MISCELLANEOUS",
                        name="SIM1",
                        file=filename,
                        extrapolate_outside=True,
                        interpolation_type=InterpolationType.LINEAR,
                    )
                ),
            )

        assert str(ve.value) == error_message

    def test_timeseries_with_int_as_date(self):
        filename = "sim1.csv"
        resource = TimeSeriesResource(MemoryResource(headers=["DATE", "HEADER1"], data=[[2012, 2013, 2014], [1, 2, 3]]))
        time_series_collection = TimeSeriesCollection.from_yaml(
            resource=resource,
            yaml_collection=TypeAdapter(YamlTimeSeriesCollection).validate_python(
                _create_timeseries_data(typ="DEFAULT", name="SIM1", file=filename),
            ),
        )
        assert time_series_collection.get_time_vector() == [
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
            datetime(2014, 1, 1),
        ]

    @pytest.mark.parametrize(
        "dates, expected",
        [
            pytest.param(
                [2012, 2013, 2014],
                [datetime(2012, 1, 1), datetime(2013, 1, 1), datetime(2014, 1, 1)],
                id="integer year only",
            ),
            pytest.param(
                [2012, "2013", 2014],
                [datetime(2012, 1, 1), datetime(2013, 1, 1), datetime(2014, 1, 1)],
                id="integer and string year mix",
            ),
            pytest.param(
                ["2012", "2013", "2014"],
                [datetime(2012, 1, 1), datetime(2013, 1, 1), datetime(2014, 1, 1)],
                id="string year only",
            ),
            pytest.param(
                ["1970.01.01", "1980.02.20", "2000.10.01"],
                [datetime(1970, 1, 1), datetime(1980, 2, 20), datetime(2000, 10, 1)],
                id="ISO-8601 date only",
            ),
            pytest.param(
                ["1970.01.01 10:10:10", "1980.02.20 11:10:01", "2000.10.01 10:20:30"],
                [datetime(1970, 1, 1, 10, 10, 10), datetime(1980, 2, 20, 11, 10, 1), datetime(2000, 10, 1, 10, 20, 30)],
                id="ISO-8601 datetime",
            ),
            pytest.param(
                ["1.01.1970", "20.02.1980", "01.10.2000"],
                [datetime(1970, 1, 1), datetime(1980, 2, 20), datetime(2000, 10, 1)],
                id="eu style date",
            ),
            pytest.param(
                ["21.01.1970 10:00:00", "12.02.1980 11:10:10", "1.12.2000 11:12:13"],
                [datetime(1970, 1, 21, 10, 0, 0), datetime(1980, 2, 12, 11, 10, 10), datetime(2000, 12, 1, 11, 12, 13)],
                id="eu style datetime",
            ),
            pytest.param(
                ["21-01-1970 23:59", "12-02-1980 11:10", "1-12-2000 11:12"],
                [datetime(1970, 1, 21, 23, 59, 0), datetime(1980, 2, 12, 11, 10, 0), datetime(2000, 12, 1, 11, 12, 0)],
                id="eu style datetime, without seconds",
            ),
        ],
    )
    def test_timeseries_valid_datetime_types(self, dates: list[str | int], expected: list[datetime]):
        filename = "sim1.csv"
        resource = TimeSeriesResource(MemoryResource(headers=["DATE", "HEADER1"], data=[dates, [1, 2, 3]]))
        time_series_collection = TimeSeriesCollection.from_yaml(
            resource=resource,
            yaml_collection=TypeAdapter(YamlTimeSeriesCollection).validate_python(
                _create_timeseries_data(typ="DEFAULT", name="SIM1", file=filename)
            ),
        )
        assert time_series_collection.get_time_vector() == expected

    @pytest.mark.parametrize(
        "dates, expected_exception_text",
        [
            pytest.param(
                ["2012.01.01", "2013.01.01", "2014"],
                "Seems like you mostly have dates in ISO-8601 format with ~67% of the lines. "
                "Found lines not conforming to this format at approx lines: [3]. "
                "These lines have format(s) ['YEAR_ONLY']",
                id="string year and some dates",
            ),
            pytest.param(
                ["13.01.1970", "1.13.1980", "01.01.2000"],
                "Month first (US style) dates are not supported, found at approx lines: [2]. "
                "Seems like you mostly have dates in DAY-FIRST format with ~67% of the lines.",
                id="mix of eu and us style date",
            ),
            pytest.param(
                ["13.01.1970 10:10:10", "01.10.1980", "01.01.2000 10:11:12"],
                "Mostly dates with time present, outliers found at approx lines: [2].",
                id="mix of date and datetime",
            ),
            pytest.param(
                ["13.01.1970 10:10:10", "1.13.1980", "01.21.2000 10:11:12"],
                "Mostly dates with time present, outliers found at approx lines: [2]. "
                "Month first (US style) dates are not supported, found at approx lines: [2 3].",
                id="mix of eu and us style date, with time",
            ),
            pytest.param(
                ["01.21.1970", "02.02.1980", "01.10.2000"],
                "Month first (US style) dates are not",
                id="us style date",
            ),
            pytest.param(
                ["01.21.1970 10:00:00", "02.02.1980 23:23:23", "01.10.2000 11:12:13"],
                "Month first (US style) dates are not",
                id="us style datetime",
            ),
            pytest.param(
                ["01.21.1970 10:00:00 AM", "02.02.1980 11:10:10pm", "01.10.2000 11:12:13 AM"],
                "AM/PM are not supported in dates",
                id="us style datetime, am/pm",
            ),
        ],
    )
    def test_timeseries_invalid_datetime_types(self, dates: list[str | int], expected_exception_text: str):
        resource = MemoryResource(headers=["DATE", "HEADER1"], data=[dates, [1, 2, 3]])
        with pytest.raises(InvalidTimeSeriesResourceException) as e:
            TimeSeriesResource(resource)
        assert expected_exception_text in str(e.value)

    @pytest.mark.parametrize(
        "header",
        ["COLUMN;1", "1", "*A", "~ABC", "A?A", "A)A", "A£", "A $", "C*", "A!A"],
    )
    def test_invalid_time_series_headers(self, header):
        filename = "test_invalid_headers.csv"

        with pytest.raises(InvalidResourceException) as ve:
            resource = TimeSeriesResource(
                MemoryResource(
                    headers=["DATE", header, "COLUMN2"],
                    data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, 3], [2, 3, 1]],
                ).validate(allow_nans=True)
            ).validate()

            TimeSeriesCollection.from_yaml(
                resource=resource,
                yaml_collection=TypeAdapter(YamlTimeSeriesCollection).validate_python(
                    _create_timeseries_data(
                        typ="DEFAULT",
                        name="SIM1",
                        file=filename,
                        extrapolate_outside=None,
                        influence_time_vector=True,
                        interpolation_type=None,
                    )
                ),
            )

        error_message = str(ve.value)
        assert "Each header value must start with a letter in the english alphabet (a-zA-Z)." in error_message

    @pytest.mark.parametrize(
        "header",
        ["COLUMN 1", "A+B", "a#b", "A:2", "A.", "A:/2", "SAT:20,20,20"],
    )
    def test_valid_time_series_headers(self, header):
        filename = "test_valid_headers.csv"
        resource = TimeSeriesResource(
            MemoryResource(
                headers=["DATE", header, "COLUMN2"],
                data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, 3], [2, 3, 1]],
            )
        )

        time_series_collection = TimeSeriesCollection.from_yaml(
            resource=resource,
            yaml_collection=TypeAdapter(YamlTimeSeriesCollection).validate_python(
                _create_timeseries_data(
                    typ="DEFAULT",
                    name="SIM1",
                    file=filename,
                    extrapolate_outside=None,
                    influence_time_vector=True,
                    interpolation_type=None,
                )
            ),
        )

        assert time_series_collection.get_time_series_references() == [header, "COLUMN2"]

    @pytest.mark.parametrize(
        "resource_name",
        ["SIM;1", "SIM*", "~@ABC", "~ABC"],
    )
    def test_invalid_resource_names(self, resource_name):
        filename = "test_invalid_resource_names.csv"

        with pytest.raises(pydantic.ValidationError) as ve:
            TypeAdapter(YamlTimeSeriesCollection).validate_python(
                _create_timeseries_data(
                    typ="DEFAULT",
                    name=resource_name,
                    file=filename,
                    extrapolate_outside=None,
                    influence_time_vector=True,
                    interpolation_type=None,
                )
            )

        error_message = str(ve.value)

        assert resource_name in error_message
        assert "String should match pattern '^[A-Za-z][A-Za-z0-9_]*$' " in error_message

    def test_undefined_type_for_miscellaneous_resource(self):
        """Check that MISCELLANEOUS fails if interpolation not defined."""

        with pytest.raises(pydantic.ValidationError) as ve:
            TypeAdapter(YamlTimeSeriesCollection).validate_python(
                _create_timeseries_data(
                    typ="MISCELLANEOUS",
                    name="SIM1",
                    file="test.csv",
                    extrapolate_outside=None,
                    influence_time_vector=True,
                )
            )

        assert isinstance(ve.value, pydantic.ValidationError)
