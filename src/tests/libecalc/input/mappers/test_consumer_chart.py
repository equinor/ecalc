import pytest
from libecalc import dto
from libecalc.common.units import Unit
from libecalc.input.mappers.facility_input import (
    _create_pump_model_single_speed_dto_model_data,
)
from libecalc.input.mappers.model import _single_speed_compressor_chart_mapper
from libecalc.input.validation_errors import ResourceValidationError
from libecalc.input.yaml_entities import Resource
from libecalc.input.yaml_keywords import EcalcYamlKeywords


@pytest.fixture
def chart_resource_with_speed():
    return Resource(
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
    return Resource(
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
    return Resource(
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
    return {
        "NAME": "pumpchart",
        "FILE": "pumpchart.csv",
        "TYPE": "PUMP_CHART_SINGLE_SPEED",
        "UNITS": {"EFFICIENCY": "PERCENTAGE", "RATE": "AM3_PER_HOUR", "HEAD": "M"},
    }


class TestSingleSpeedChart:
    def test_valid_with_speed(self, pump_chart, chart_resource_with_speed):
        """Test that speed can be specified. Note: 1.0 and 1 is considered equal."""
        pump_model_dto = _create_pump_model_single_speed_dto_model_data(
            resource=chart_resource_with_speed,
            facility_data=pump_chart,
        )
        assert pump_model_dto == dto.PumpModel(
            chart=dto.SingleSpeedChart(
                rate_actual_m3_hour=[6.0, 6.0],
                polytropic_head_joule_per_kg=[
                    Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(x)
                    for x in [7.0, 7.0]
                ],
                efficiency_fraction=[0.08, 0.08],
                speed_rpm=5.0,
            ),
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            head_margin=0,
        )

    def test_valid_without_speed(self, pump_chart, chart_resource_without_speed):
        pump_model_dto = _create_pump_model_single_speed_dto_model_data(
            resource=chart_resource_without_speed,
            facility_data=pump_chart,
        )
        assert pump_model_dto == dto.PumpModel(
            chart=dto.SingleSpeedChart(
                rate_actual_m3_hour=[6.0, 6.0],
                polytropic_head_joule_per_kg=[
                    Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(x)
                    for x in [7.0, 7.0]
                ],
                efficiency_fraction=[0.08, 0.08],
                speed_rpm=1,
            ),
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1,
            head_margin=0,
        )

    def test_invalid_unequal_speed(self, pump_chart, chart_resource_unequal_speed):
        with pytest.raises(ResourceValidationError) as exception_info:
            _create_pump_model_single_speed_dto_model_data(
                resource=chart_resource_unequal_speed,
                facility_data=pump_chart,
            )

        assert "All speeds should be equal when creating a single-speed chart." in str(exception_info.value)


@pytest.fixture
def compressor_chart():
    return {
        "NAME": "compressorchart",
        "TYPE": "COMPRESSOR_CHART",
        "CHART_TYPE": "SINGLE_SPEED",
        "UNITS": {
            "EFFICIENCY": "PERCENTAGE",
            "RATE": "AM3_PER_HOUR",
            "HEAD": "KJ_PER_KG",
        },
        "CURVE": {"FILE": "compressorchart.csv"},
    }


class TestCompressorChartSingleSpeed:
    def test_valid_with_speed(self, compressor_chart, chart_resource_with_speed):
        """Test that speed can be specified. Note: 1.0 and 1 is considered equal."""
        chart_dto = _single_speed_compressor_chart_mapper(
            model_config=compressor_chart, resources={"compressorchart.csv": chart_resource_with_speed}
        )
        assert chart_dto == dto.SingleSpeedChart(
            rate_actual_m3_hour=[6.0, 6.0],
            polytropic_head_joule_per_kg=[7000.0, 7000.0],
            efficiency_fraction=[0.08, 0.08],
            speed_rpm=5.0,
        )

    def test_valid_without_speed(self, compressor_chart, chart_resource_without_speed):
        """Test that speed can be specified. Note: 1.0 and 1 is considered equal."""
        chart_dto = _single_speed_compressor_chart_mapper(
            model_config=compressor_chart, resources={"compressorchart.csv": chart_resource_without_speed}
        )
        assert chart_dto == dto.SingleSpeedChart(
            rate_actual_m3_hour=[6.0, 6.0],
            polytropic_head_joule_per_kg=[7000.0, 7000.0],
            efficiency_fraction=[0.08, 0.08],
            speed_rpm=1,
        )

    def test_invalid_unequal_speed(self, compressor_chart, chart_resource_unequal_speed):
        with pytest.raises(ResourceValidationError) as exception_info:
            _single_speed_compressor_chart_mapper(
                model_config=compressor_chart, resources={"compressorchart.csv": chart_resource_unequal_speed}
            )

        assert "All speeds should be equal when creating a single-speed chart." in str(exception_info.value)
