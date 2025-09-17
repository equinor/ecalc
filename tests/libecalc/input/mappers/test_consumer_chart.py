import pytest

from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.common.serializable_chart import ChartDTO, ChartCurveDTO
from libecalc.presentation.yaml.mappers.facility_input import (
    _create_pump_model_single_speed_dto_model_data,
)
from libecalc.presentation.yaml.mappers.model import (
    InvalidChartResourceException,
    _single_speed_compressor_chart_mapper,
)
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlPumpChartSingleSpeed,
    YamlPumpChartUnits,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import YamlSingleSpeedChart, YamlUnits
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile


@pytest.fixture
def chart_resource_with_speed():
    return MemoryResource(
        data=[
            [5.0, 5],
            [6, 6],
            [7, 7],
            [8, 8],
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
            [6, 6],
            [7, 7],
            [8, 8],
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
        units=YamlPumpChartUnits(efficiency="PERCENTAGE", rate="AM3_PER_HOUR", head="M"),
    )


class TestSingleSpeedChart:
    def test_valid_with_speed(self, pump_chart, chart_resource_with_speed):
        """Test that speed can be specified. Note: 1.0 and 1 is considered equal."""
        pump_model = _create_pump_model_single_speed_dto_model_data(
            resource=chart_resource_with_speed,
            facility_data=pump_chart,
        )

        assert pump_model.pump_chart.curves[0].speed == 5.0

    def test_valid_without_speed(self, pump_chart, chart_resource_without_speed):
        pump_model = _create_pump_model_single_speed_dto_model_data(
            resource=chart_resource_without_speed,
            facility_data=pump_chart,
        )

        # Speed set to 1.0 if header not found
        assert pump_model.pump_chart.curves[0].speed == 1.0

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
        chart_dto = _single_speed_compressor_chart_mapper(
            model_config=compressor_chart, resources={"compressorchart.csv": chart_resource_with_speed}
        )
        assert chart_dto == ChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[6.0, 6.0],
                    polytropic_head_joule_per_kg=[7000.0, 7000.0],
                    efficiency_fraction=[0.08, 0.08],
                    speed_rpm=5.0,
                )
            ]
        )

    def test_valid_without_speed(self, compressor_chart, chart_resource_without_speed):
        """Test that speed can be specified. Note: 1.0 and 1 is considered equal."""
        chart_dto = _single_speed_compressor_chart_mapper(
            model_config=compressor_chart, resources={"compressorchart.csv": chart_resource_without_speed}
        )
        assert chart_dto == ChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[6.0, 6.0],
                    polytropic_head_joule_per_kg=[7000.0, 7000.0],
                    efficiency_fraction=[0.08, 0.08],
                    speed_rpm=1.0,
                )
            ]
        )

    def test_invalid_unequal_speed(self, compressor_chart, chart_resource_unequal_speed):
        with pytest.raises(InvalidChartResourceException) as exception_info:
            _single_speed_compressor_chart_mapper(
                model_config=compressor_chart, resources={"compressorchart.csv": chart_resource_unequal_speed}
            )

        assert "All speeds should be equal when creating a single-speed chart." in str(exception_info.value)
