import math
from datetime import datetime
from typing import Dict, Optional

import pytest
from libecalc.dto import TimeSeriesType
from libecalc.dto.types import InterpolationType
from libecalc.presentation.yaml.mappers.variables_mapper.time_series_collection import (
    MiscellaneousTimeSeriesCollection,
)
from libecalc.presentation.yaml.mappers.variables_mapper.time_series_collection_mapper import (
    TimeSeriesCollectionMapper,
)
from libecalc.presentation.yaml.validation_errors import DtoValidationError
from libecalc.presentation.yaml.yaml_entities import Resource
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


def _create_timeseries_data(
    typ: TimeSeriesType,
    name: str,
    file: str,
    influence_time_vector: Optional[bool] = None,
    extrapolate_outside: Optional[bool] = None,
    interpolation_type: Optional[InterpolationType] = None,
) -> Dict:
    timeseries_dict = {
        EcalcYamlKeywords.type: typ.value,
        EcalcYamlKeywords.name: name,
        EcalcYamlKeywords.file: file,
    }

    if influence_time_vector is not None:
        timeseries_dict[EcalcYamlKeywords.time_series_influence_time_vector] = influence_time_vector

    if extrapolate_outside is not None:
        timeseries_dict[EcalcYamlKeywords.time_series_extrapolate_outside_defined] = extrapolate_outside

    if interpolation_type is not None:
        timeseries_dict[EcalcYamlKeywords.time_series_interpolation_type] = interpolation_type

    return timeseries_dict


class TestTimeSeries:
    parameterized_valid_timeseries_data = [
        (
            TimeSeriesType.MISCELLANEOUS,
            MiscellaneousTimeSeriesCollection,
            TimeSeriesType.MISCELLANEOUS,
            True,
            True,
            InterpolationType.LEFT,
            True,
        )
    ]

    @pytest.mark.parametrize(
        "typ_string, typ_class, typ_enum, extrapolate, influence_time_vector, interpolation_type, extrapolate_result",
        parameterized_valid_timeseries_data,
    )
    def test_valid_minimal_timeserie_different_types(
        self,
        typ_string,
        typ_class,
        typ_enum,
        extrapolate,
        influence_time_vector,
        interpolation_type,
        extrapolate_result,
    ):
        filename = "test.csv"
        resources = {filename: Resource(headers=["DATE", "OIL_PROD"], data=[["01.01.2017"], [5016]])}

        timeseries_mapper = TimeSeriesCollectionMapper(resources=resources)
        timeseries_model = timeseries_mapper.from_yaml_to_dto(
            _create_timeseries_data(
                typ=typ_string,
                name="fuel_price",
                file=filename,
                extrapolate_outside=extrapolate,
                interpolation_type=interpolation_type,
                influence_time_vector=influence_time_vector,
            )
        )

        assert isinstance(timeseries_model, typ_class)
        assert timeseries_model.typ == typ_enum
        assert timeseries_model.headers == ["OIL_PROD"]
        assert timeseries_model.time_vector == [datetime(2017, 1, 1)]
        assert timeseries_model.columns == [[5016]]
        assert timeseries_model.extrapolate_outside_defined_time_interval is extrapolate_result
        assert timeseries_model.influence_time_vector is True
        assert timeseries_model.interpolation_type == InterpolationType.LEFT

    def test_valid_time_series_multiple_columns(self):
        filename = "test_multiple_columns.csv"
        resources = {
            filename: Resource(
                headers=["DATE", "COLUMN1", "COLUMN2", "COLUMN3"],
                data=[["01.01.2015", "01.01.2016"], [1, 2], [3, 4], [5, 6]],
            )
        }
        time_series_mapper = TimeSeriesCollectionMapper(resources=resources)
        time_series_dto = time_series_mapper.from_yaml_to_dto(
            _create_timeseries_data(
                typ=TimeSeriesType.DEFAULT,
                name="SIM1",
                file=filename,
                extrapolate_outside=None,
                influence_time_vector=True,
                interpolation_type=None,
            )
        )

        assert time_series_dto.columns == [[1, 2], [3, 4], [5, 6]]
        assert time_series_dto.time_vector == [datetime(2015, 1, 1), datetime(2016, 1, 1)]
        assert time_series_dto.headers == ["COLUMN1", "COLUMN2", "COLUMN3"]
        assert time_series_dto.typ == TimeSeriesType.DEFAULT

    def test_valid_time_series_unsorted(self):
        filename = "test_unsorted.csv"
        resources = {
            filename: Resource(
                headers=["DATE", "COLUMN1", "COLUMN2"],
                data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, 3], [2, 3, 1]],
            )
        }
        time_series_mapper = TimeSeriesCollectionMapper(resources=resources)
        time_series_dto = time_series_mapper.from_yaml_to_dto(
            _create_timeseries_data(
                typ=TimeSeriesType.DEFAULT,
                name="SIM1",
                file=filename,
                extrapolate_outside=None,
                influence_time_vector=True,
                interpolation_type=None,
            )
        )

        assert time_series_dto.columns == [
            [3, 1, 2],
            [1, 2, 3],
        ]
        assert time_series_dto.time_vector == [datetime(1900, 1, 1), datetime(2015, 1, 1), datetime(2016, 1, 1)]
        assert time_series_dto.headers == ["COLUMN1", "COLUMN2"]
        assert time_series_dto.typ == TimeSeriesType.DEFAULT

    parameterized_invalid_timeseries_data = [
        # headers, data mismatch (+1)
        (
            ["DATE", "OIL_PROD", "BVBV"],
            [["01.01.2017"], [5016]],
            "The number of columns provided do not match for header and data: data: 1, headers: 2",
        ),
        # headers, data mismatch (-1)
        (
            ["DATE", "OIL_PROD"],
            [["01.01.2017"], [5016], [232]],
            "The number of columns provided do not match for header and data: data: 2, headers: 1",
        ),
        # no data
        (
            ["DATE", "DUMMY"],
            [["01.01.2017"]],
            "Data vector must at least have one column",
        ),
        # no time
        (
            ["DATE", "OIL_PROD"],
            [[], [5016]],
            "Time vectors must have at least one record",
        ),
        # no headers
        (
            [],
            [["01.01.2017"], [5016]],
            "Headers must at least have one column",
        ),
        # mismatch data, time
        (
            ["DATE", "OIL_PROD"],
            [["01.01.2017", "01.01.2018"], [5016]],
            "The number of records for times and data do not match: data: 1, time_vector: 2",
        ),
        # mismatch data, time
        (
            ["DATE", "OIL_PROD"],
            [["01.01.2017"], [5016, 5026]],
            "The number of records for times and data do not match: data: 2, time_vector: 1",
        ),
        # no data cols
        (
            ["DATE", "HEADER"],
            [["01.01.2017"]],
            "Data vector must at least have one column",
        ),
        # duplicate dates
        (
            ["DATE", "HEADER"],
            [["01.01.2015", "01.01.2016", "01.01.2017", "01.01.2017"], [5016, 5036, 5026, 5216]],
            "The list of dates have duplicates. Duplicated dates are currently not supported.",
        ),
    ]

    @pytest.mark.parametrize(
        "headers, columns, error_message",
        parameterized_invalid_timeseries_data,
    )
    def test_invalid_timeseries(self, headers, columns, error_message):
        filename = "test.csv"
        resources = {
            filename: Resource(
                headers=headers,
                data=columns,
            )
        }

        timeseries_mapper = TimeSeriesCollectionMapper(resources=resources)
        with pytest.raises(DtoValidationError) as ve:
            timeseries_mapper.from_yaml_to_dto(
                _create_timeseries_data(
                    typ=TimeSeriesType.MISCELLANEOUS,
                    name="fuel_price",
                    file=filename,
                    extrapolate_outside=True,
                    interpolation_type=InterpolationType.LINEAR,
                )
            )

        assert str(error_message) in str(ve.value)

    def test_timeseries_with_int_as_date(self):
        filename = "sim1.csv"
        resources = {filename: Resource(headers=["DATE", "HEADER1"], data=[[2012, 2013, 2014], [1, 2, 3]])}
        timeseries_mapper = TimeSeriesCollectionMapper(resources=resources)
        timeseries_dto = timeseries_mapper.from_yaml_to_dto(
            _create_timeseries_data(typ=TimeSeriesType.DEFAULT, name="SIM1", file=filename)
        )
        assert timeseries_dto.time_vector == [
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
            datetime(2014, 1, 1),
        ]

    @pytest.mark.parametrize(
        "header",
        ["COLUMN;1", "1", "*A", "~ABC", "A?A", "A)A", "A£", "A $", "C*", "A!A"],
    )
    def test_invalid_time_series_headers(self, header):
        filename = "test_invalid_headers.csv"
        resources = {
            filename: Resource(
                headers=["DATE", header, "COLUMN2"],
                data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, 3], [2, 3, 1]],
            )
        }
        time_series_mapper = TimeSeriesCollectionMapper(resources=resources)

        with pytest.raises(DtoValidationError) as ve:
            time_series_mapper.from_yaml_to_dto(
                _create_timeseries_data(
                    typ=TimeSeriesType.DEFAULT,
                    name="SIM1",
                    file=filename,
                    extrapolate_outside=None,
                    influence_time_vector=True,
                    interpolation_type=None,
                )
            )
        assert r'string does not match regex "^[A-Za-z][A-Za-z0-9_.,\-\s#+:\/]*$' in str(ve.value)

    @pytest.mark.parametrize(
        "header",
        ["COLUMN 1", "A+B", "a#b", "A:2", "A.", "A:/2", "SAT:20,20,20"],
    )
    def test_valid_time_series_headers(self, header):
        filename = "test_valid_headers.csv"
        resources = {
            filename: Resource(
                headers=["DATE", header, "COLUMN2"],
                data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, 3], [2, 3, 1]],
            )
        }
        time_series_mapper = TimeSeriesCollectionMapper(resources=resources)
        time_series_dto = time_series_mapper.from_yaml_to_dto(
            _create_timeseries_data(
                typ=TimeSeriesType.DEFAULT,
                name="SIM1",
                file=filename,
                extrapolate_outside=None,
                influence_time_vector=True,
                interpolation_type=None,
            )
        )

        assert time_series_dto.headers == [header, "COLUMN2"]

    @pytest.mark.parametrize(
        "resource_name",
        ["SIM;1", "SIM*", "~@ABC", "~ABC"],
    )
    def test_invalid_resource_names(self, resource_name):
        filename = "test_invalid_resource_names.csv"
        resources = {
            filename: Resource(
                headers=["DATE", "COLUMN1", "COLUMN2"],
                data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, 3], [2, 3, 1]],
            )
        }
        time_series_mapper = TimeSeriesCollectionMapper(resources=resources)

        with pytest.raises(DtoValidationError) as ve:
            time_series_mapper.from_yaml_to_dto(
                _create_timeseries_data(
                    typ=TimeSeriesType.DEFAULT,
                    name=resource_name,
                    file=filename,
                    extrapolate_outside=None,
                    influence_time_vector=True,
                    interpolation_type=None,
                )
            )
        assert 'string does not match regex "^[A-Za-z][A-Za-z0-9_]*$' in str(ve.value)

    def test_interpretation_of_interpolation_type_for_default_resource(self):
        """Check default interpolation for DEFAULT time series."""
        filename = "test_interpretation_of_rate_interpolation_type_for_reservoir_resource.csv"
        resources = {
            filename: Resource(
                headers=["DATE", "GAS_PROD"],
                data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, 3]],
            )
        }
        time_series_mapper = TimeSeriesCollectionMapper(resources=resources)

        time_series_explicit_none = time_series_mapper.from_yaml_to_dto(
            _create_timeseries_data(
                typ=TimeSeriesType.DEFAULT,
                name="SIM1",
                file=filename,
                extrapolate_outside=None,
                influence_time_vector=True,
                interpolation_type=None,
            )
        )
        assert time_series_explicit_none.interpolation_type == InterpolationType.RIGHT

        time_series_implicit_none = time_series_mapper.from_yaml_to_dto(
            _create_timeseries_data(
                typ=TimeSeriesType.DEFAULT,
                name="SIM1",
                file=filename,
                extrapolate_outside=None,
                influence_time_vector=True,
            )
        )

        assert time_series_implicit_none.interpolation_type == InterpolationType.RIGHT

    def test_undefined_type_for_miscellaneous_resource(self):
        """Check that MISCELLANEOUS fails if interpolation not defined."""
        filename = "test_interpretation_of_rate_interpolation_type_for_reservoir_resource.csv"
        resources = {
            filename: Resource(
                headers=["DATE", "GAS_PROD"],
                data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, 3]],
            )
        }
        time_series_mapper = TimeSeriesCollectionMapper(resources=resources)

        with pytest.raises(DtoValidationError) as ve:
            time_series_mapper.from_yaml_to_dto(
                _create_timeseries_data(
                    typ=TimeSeriesType.MISCELLANEOUS,
                    name="SIM1",
                    file=filename,
                    extrapolate_outside=None,
                    influence_time_vector=True,
                )
            )
        assert isinstance(ve.value, DtoValidationError)

    def test_left_interpolation_type_for_miscellaneous_resource(self):
        """Check that LEFT is used when specified for MISCELLANEOUS."""
        filename = "test_interpretation_of_rate_interpolation_type_for_reservoir_resource.csv"
        resources = {
            filename: Resource(
                headers=["DATE", "GAS_PROD"],
                data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, 3]],
            )
        }
        time_series_mapper = TimeSeriesCollectionMapper(resources=resources)

        time_series = time_series_mapper.from_yaml_to_dto(
            _create_timeseries_data(
                typ=TimeSeriesType.MISCELLANEOUS,
                name="SIM1",
                file=filename,
                extrapolate_outside=None,
                influence_time_vector=True,
                interpolation_type=InterpolationType.LEFT,
            )
        )
        assert time_series.interpolation_type == InterpolationType.LEFT

    def test_error_if_nan_data(self):
        filename = "test_invalid_data.csv"
        resources = {
            filename: Resource(
                headers=["DATE", "COLUMN2"],
                data=[["01.01.2015", "01.01.2016", "01.01.1900"], [1, 2, math.nan]],
            )
        }
        time_series_mapper = TimeSeriesCollectionMapper(resources=resources)
        with pytest.raises(DtoValidationError) as exc_info:
            time_series_mapper.from_yaml_to_dto(
                _create_timeseries_data(
                    typ=TimeSeriesType.DEFAULT,
                    name="SIM1",
                    file=filename,
                    extrapolate_outside=None,
                    influence_time_vector=True,
                    interpolation_type=None,
                )
            )

        assert "The timeseries column 'SIM1;COLUMN2' contains empty values." in str(exc_info.value)
