import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import InvalidColumnException, InvalidResourceException, ResourceFileMark
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData
from libecalc.presentation.yaml.mappers.facility_input import (
    _create_pump_model_single_speed_dto_model_data,
)
from libecalc.presentation.yaml.mappers.model import (
    InvalidChartResourceException,
    single_speed_compressor_chart_mapper,
)
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlPumpChartSingleSpeed,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlCurve,
    YamlSingleSpeedChart,
    YamlUnits,
)
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile


@pytest.fixture
def chart_resource_with_speed():
    return MemoryResource(
        data=[
            [5.0, 5],  # speed
            [6, 7],  # rate
            [8, 7],  # head
            [8, 8],  # efficiency
        ],  # float and int with equal value should count as equal.
        headers=[
            EcalcYamlKeywords.consumer_chart_speed,
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )


@pytest.fixture
def chart_resource_without_speed():
    return MemoryResource(
        data=[
            [6, 7],  # rate
            [8, 7],  # head
            [8, 8],  # efficiency
        ],
        headers=[
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )


@pytest.fixture
def chart_resource_unequal_speed():
    return MemoryResource(
        data=[
            [5, 6],
            [6, 6],
            [7, 7],
            [8, 8],
        ],
        headers=[
            EcalcYamlKeywords.consumer_chart_speed,
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )


@pytest.fixture
def pump_chart():
    return YamlPumpChartSingleSpeed(
        name="pumpchart",
        file="pumpchart.csv",
        type="PUMP_CHART_SINGLE_SPEED",
        units=YamlUnits(efficiency="PERCENTAGE", rate="AM3_PER_HOUR", head="M"),
    )


class TestSingleSpeedChart:
    def test_valid_with_speed(self, pump_chart, chart_resource_with_speed):
        """Test that speed can be specified. Note: 1.0 and 1 is considered equal."""
        chart = UserDefinedChartData.from_resource(
            chart_resource_with_speed,
            units=pump_chart.units,
            is_single_speed=True,
        )

        assert chart.get_original_curves()[0].speed == 5.0

    def test_valid_without_speed(self, pump_chart, chart_resource_without_speed):
        chart = UserDefinedChartData.from_resource(
            chart_resource_without_speed,
            units=pump_chart.units,
            is_single_speed=True,
        )
        # Speed set to 1.0 if header not found
        assert chart.get_original_curves()[0].speed == 1.0

    def test_invalid_unequal_speed(self, pump_chart, chart_resource_unequal_speed):
        with pytest.raises(InvalidResourceException) as exception_info:
            _create_pump_model_single_speed_dto_model_data(
                resource=chart_resource_unequal_speed,
                facility_data=pump_chart,
            )

        assert "All speeds should be equal when creating a single-speed chart." in str(exception_info.value)


@pytest.fixture
def compressor_chart():
    return YamlSingleSpeedChart(
        name="compressorchart",
        type="COMPRESSOR_CHART",
        chart_type="SINGLE_SPEED",
        units=YamlUnits(
            efficiency="PERCENTAGE",
            rate="AM3_PER_HOUR",
            head="KJ_PER_KG",
        ),
        curve=YamlFile(file="compressorchart.csv"),
    )


class TestCompressorChartSingleSpeed:
    def test_valid_with_speed(self, compressor_chart, chart_resource_with_speed):
        """Test that speed can be specified. Note: 1.0 and 1 is considered equal."""
        chart = single_speed_compressor_chart_mapper(
            model_config=compressor_chart,
            resources={"compressorchart.csv": chart_resource_with_speed},
            control_margin=None,
        )
        curves = chart.get_original_curves()
        assert len(curves) == 1
        curve = curves[0]
        assert curve.speed == 5
        assert curve.rate == [6.0, 7.0]
        assert curve.head == [8000.0, 7000.0]
        assert curve.efficiency == [0.08, 0.08]

    def test_valid_without_speed(self, compressor_chart, chart_resource_without_speed):
        """Test that speed can be specified. Note: 1.0 and 1 is considered equal."""
        chart = single_speed_compressor_chart_mapper(
            model_config=compressor_chart,
            resources={"compressorchart.csv": chart_resource_without_speed},
            control_margin=None,
        )
        curves = chart.get_original_curves()
        assert len(curves) == 1
        curve = curves[0]
        assert curve.speed == 1
        assert curve.rate == [6.0, 7.0]
        assert curve.head == [8000.0, 7000.0]
        assert curve.efficiency == [0.08, 0.08]

    def test_invalid_unequal_speed(self, compressor_chart, chart_resource_unequal_speed):
        with pytest.raises(InvalidChartResourceException) as exception_info:
            single_speed_compressor_chart_mapper(
                model_config=compressor_chart,
                resources={"compressorchart.csv": chart_resource_unequal_speed},
                control_margin=None,
            )

        assert "All speeds should be equal when creating a single-speed chart." in str(exception_info.value)


def test_head_error_reports_values_and_unit_from_file():
    resource = MemoryResource(
        data=[[1000.0, 2000.0, 3000.0], [80.0, 90.0, 70.0], [0.75, 0.75, 0.75]],
        headers=[
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )
    with pytest.raises(InvalidResourceException) as exc_info:
        UserDefinedChartData.from_resource(resource, units=YamlUnits(head="KJ_PER_KG"), is_single_speed=True)

    message = str(exc_info.value)
    assert (
        "Row 2 (rate 2000.0 AM3_PER_HOUR, head 90.0 KJ_PER_KG) does not have a lower head than "
        "row 1 (rate 1000.0 AM3_PER_HOUR, head 80.0 KJ_PER_KG)"
    ) in message
    assert "3000.0" not in message


def test_variable_speed_head_error_names_the_failing_speed():
    resource = MemoryResource(
        data=[
            [1000.0, 1000.0, 2000.0, 2000.0],
            [100.0, 200.0, 100.0, 200.0],
            [50.0, 40.0, 60.0, 70.0],
            [0.7, 0.7, 0.7, 0.7],
        ],
        headers=[
            EcalcYamlKeywords.consumer_chart_speed,
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )
    with pytest.raises(InvalidResourceException) as exc_info:
        UserDefinedChartData.from_resource(resource, units=YamlUnits(head="KJ_PER_KG"), is_single_speed=False)

    message = str(exc_info.value)
    assert "at speed 2000.0" in message
    assert "Row 4 (rate 200.0 AM3_PER_HOUR, head 70.0 KJ_PER_KG) does not have a lower head than row 3" in message


@pytest.mark.parametrize(
    "unit, efficiency, expected",
    [
        ("PERCENTAGE", [80.0, 120.0], "between 0 and 100 PERCENTAGE. Row 2 has 120.0."),
        ("FRACTION", [0.8, 1.2], "between 0 and 1 FRACTION. Row 2 has 1.2."),
    ],
)
def test_efficiency_error_reports_values_in_file_units(unit, efficiency, expected):
    resource = MemoryResource(
        data=[[1000.0, 2000.0], [200.0, 100.0], efficiency],
        headers=[
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )
    with pytest.raises(InvalidResourceException) as exc_info:
        UserDefinedChartData.from_resource(resource, units=YamlUnits(efficiency=unit), is_single_speed=True)

    assert expected in str(exc_info.value)


def test_efficiency_error_marks_the_file_row():
    resource = MemoryResource(
        data=[[1000.0, 2000.0, 3000.0], [300.0, 200.0, 100.0], [80.0, 120.0, 70.0]],
        headers=[
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )
    with pytest.raises(InvalidResourceException) as exc_info:
        UserDefinedChartData.from_resource(resource, units=YamlUnits(), is_single_speed=True)

    assert exc_info.value.file_mark == ResourceFileMark(row=2, column=EcalcYamlKeywords.consumer_chart_efficiency)
    assert "Row 2 has 120.0" in str(exc_info.value)


def test_variable_speed_head_error_marks_the_row_in_the_file():
    resource = MemoryResource(
        data=[
            [1000.0, 2000.0, 1000.0, 2000.0],
            [100.0, 100.0, 200.0, 200.0],
            [50.0, 60.0, 40.0, 70.0],
            [0.7, 0.7, 0.7, 0.7],
        ],
        headers=[
            EcalcYamlKeywords.consumer_chart_speed,
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )
    with pytest.raises(InvalidResourceException) as exc_info:
        UserDefinedChartData.from_resource(resource, units=YamlUnits(head="KJ_PER_KG"), is_single_speed=False)

    assert exc_info.value.file_mark == ResourceFileMark(row=4, column=EcalcYamlKeywords.consumer_chart_head)
    assert "Row 4 (rate 200.0 AM3_PER_HOUR, head 70.0 KJ_PER_KG) does not have a lower head than row 2" in str(
        exc_info.value
    )


def test_head_error_with_nan_is_a_validation_error():
    resource = MemoryResource(
        data=[[1000.0, 2000.0], [200.0, float("nan")], [0.7, 0.7]],
        headers=[
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )
    with pytest.raises(InvalidResourceException) as exc_info:
        UserDefinedChartData.from_resource(resource, units=YamlUnits(), is_single_speed=True)

    assert exc_info.value.file_mark == ResourceFileMark(row=2, column=EcalcYamlKeywords.consumer_chart_head)


def test_unequal_column_lengths_is_a_validation_error():
    resource = MemoryResource(
        data=[[1.0, 2.0], [10.0, 5.0], [70.0, 70.0, 150.0]],
        headers=[
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )
    with pytest.raises(InvalidResourceException, match="equal number of points"):
        UserDefinedChartData.from_resource(resource, units=YamlUnits(), is_single_speed=True)


def test_head_error_with_nan_in_first_point_marks_that_row():
    resource = MemoryResource(
        data=[[1000.0, 2000.0], [float("nan"), 100.0], [0.7, 0.7]],
        headers=[
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )
    with pytest.raises(InvalidResourceException) as exc_info:
        UserDefinedChartData.from_resource(resource, units=YamlUnits(), is_single_speed=True)

    assert exc_info.value.file_mark == ResourceFileMark(row=1, column=EcalcYamlKeywords.consumer_chart_head)


def test_variable_speed_head_error_with_unsorted_rates_and_mixed_speeds():
    resource = MemoryResource(
        data=[
            [1000.0, 2000.0, 1000.0, 2000.0, 1000.0],
            [300.0, 100.0, 100.0, 300.0, 200.0],
            [10.0, 60.0, 50.0, 40.0, 60.0],
            [0.7, 0.7, 0.7, 0.7, 0.7],
        ],
        headers=[
            EcalcYamlKeywords.consumer_chart_speed,
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )
    with pytest.raises(InvalidResourceException) as exc_info:
        UserDefinedChartData.from_resource(resource, units=YamlUnits(head="KJ_PER_KG"), is_single_speed=False)

    assert exc_info.value.file_mark == ResourceFileMark(row=5, column=EcalcYamlKeywords.consumer_chart_head)
    assert "at speed 1000.0" in str(exc_info.value)
    assert "Row 5 (rate 200.0 AM3_PER_HOUR, head 60.0 KJ_PER_KG) does not have a lower head than row 3" in str(
        exc_info.value
    )


def test_missing_speed_marks_the_row():
    resource = MemoryResource(
        data=[[1000.0, float("nan")], [100.0, 200.0], [50.0, 40.0], [0.7, 0.7]],
        headers=[
            EcalcYamlKeywords.consumer_chart_speed,
            EcalcYamlKeywords.consumer_chart_rate,
            EcalcYamlKeywords.consumer_chart_head,
            EcalcYamlKeywords.consumer_chart_efficiency,
        ],
    )
    with pytest.raises(InvalidColumnException) as exc_info:
        UserDefinedChartData.from_resource(resource, units=YamlUnits(), is_single_speed=False)

    assert exc_info.value.file_mark == ResourceFileMark(row=2, column=EcalcYamlKeywords.consumer_chart_speed)


@pytest.mark.parametrize("curve_count, speed_text", [(1, False), (2, True)])
def test_inline_yaml_head_error_names_the_point(curve_count, speed_text):
    curves = [
        YamlCurve(speed=1000.0 * (i + 1), rate=[100.0, 200.0], head=[50.0, 60.0], efficiency=[0.7, 0.7])
        for i in range(curve_count)
    ]
    with pytest.raises(EcalcValidationException) as exc_info:
        UserDefinedChartData.from_yaml_curves(curves, units=YamlUnits())

    message = str(exc_info.value)
    assert not isinstance(exc_info.value, InvalidResourceException)
    assert "Point 2" in message
    assert ("at speed 1000.0" in message) is speed_text
