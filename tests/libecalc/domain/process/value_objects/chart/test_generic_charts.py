import pytest

from libecalc.domain.component_validation_error import ProcessChartValueValidationException
from libecalc.domain.process.value_objects.chart.generic import GenericChartFromDesignPoint, GenericChartFromInput


class TestGenericFromDesignPointCompressorChart:
    def test_create_object(self):
        GenericChartFromDesignPoint(
            polytropic_efficiency_fraction=0.8,
            design_rate_actual_m3_per_hour=7500.0,
            design_polytropic_head_J_per_kg=55000,
        )

    def test_invalid_polytropic_efficiency(self):
        with pytest.raises(ProcessChartValueValidationException) as e:
            GenericChartFromDesignPoint(
                polytropic_efficiency_fraction=1.8,
                design_rate_actual_m3_per_hour=7500.0,
                design_polytropic_head_J_per_kg=55000,
            )
        assert "polytropic_efficiency_fraction must be greater than 0 and less than or equal to 1" in str(e.value)

    def test_invalid_design_rate(self):
        with pytest.raises(ProcessChartValueValidationException) as e:
            GenericChartFromDesignPoint(
                polytropic_efficiency_fraction=0.8,
                design_rate_actual_m3_per_hour="invalid_design_rate",
                design_polytropic_head_J_per_kg=55000,
            )
        assert "design_rate_actual_m3_per_hour must be a number" in str(e.value)


class TestGenericFromInputCompressorChart:
    def test_create_object(self):
        GenericChartFromInput(polytropic_efficiency_fraction=0.8)

    def test_invalid(self):
        with pytest.raises(ProcessChartValueValidationException) as e:
            GenericChartFromInput(polytropic_efficiency_fraction="str")
        assert "polytropic_efficiency_fraction must be a number" in str(e.value)
