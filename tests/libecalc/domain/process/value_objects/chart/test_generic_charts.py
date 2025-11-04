import pytest

from libecalc.domain.component_validation_error import ProcessChartValueValidationException
from libecalc.domain.process.value_objects.chart.generic import GenericChartFromInput


class TestGenericFromInputCompressorChart:
    def test_create_object(self):
        GenericChartFromInput(polytropic_efficiency_fraction=0.8)

    def test_invalid(self):
        with pytest.raises(ProcessChartValueValidationException) as e:
            GenericChartFromInput(polytropic_efficiency_fraction="str")
        assert "polytropic_efficiency_fraction must be a number" in str(e.value)
