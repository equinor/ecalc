from typing import Self

from libecalc.testing.yaml_builder import Builder
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlUnits,
    YamlCurve,
    YamlRateUnits,
    YamlHeadUnits,
    YamlEfficiencyUnits,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import YamlControlMarginUnits
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import YamlItem, YamlProcessPipeline

from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlLiquidRemover,
    YamlTemperatureSetter,
    YamlPressureDropper,
    YamlCompressorModelChart,
    YamlCompressor,
    YamlControlMargin,
    YamlCompressorChart,
    YamlProcessUnit,
)


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------


class YamlCurveBuilder(Builder[YamlCurve]):
    def __init__(self):
        self.speed = None
        self.rate = None
        self.head = None
        self.efficiency = None

    def with_speed(self, speed: float) -> Self:
        self.speed = speed
        return self

    def with_rate(self, rate: list[float]) -> Self:
        self.rate = rate
        return self

    def with_head(self, head: list[float]) -> Self:
        self.head = head
        return self

    def with_efficiency(self, efficiency: list[float]) -> Self:
        self.efficiency = efficiency
        return self

    def with_test_data(self) -> Self:
        self.speed = 10000.0
        self.rate = [3000.0, 4000.0, 5000.0]
        self.head = [100000.0, 90000.0, 75000.0]
        self.efficiency = [0.72, 0.74, 0.70]
        return self


class YamlCompressorChartBuilder(Builder[YamlCompressorChart]):
    def __init__(self):
        self.curves = None
        self.units = None

    def with_curves(self, curves: list[YamlCurve]) -> Self:
        self.curves = curves
        return self

    def with_units(self, units: YamlUnits) -> Self:
        self.units = units
        return self

    def with_test_data(self) -> Self:
        self.curves = [YamlCurveBuilder().with_test_data().validate()]
        self.units = YamlUnits(
            rate=YamlRateUnits.AM3_PER_HOUR,
            head=YamlHeadUnits.M,
            efficiency=YamlEfficiencyUnits.PERCENTAGE,
        )
        return self


class YamlCompressorModelChartBuilder(Builder[YamlCompressorModelChart]):
    def __init__(self):
        self.type = "COMPRESSOR_CHART"
        self.chart = None
        self.control_margin = None

    def with_chart(self, chart: YamlCompressorChart) -> Self:
        self.chart = chart
        return self

    def with_control_margin(self, value: float, unit: YamlControlMarginUnits = YamlControlMarginUnits.FRACTION) -> Self:
        self.control_margin = YamlControlMargin(unit=unit, value=value)
        return self

    def with_test_data(self) -> Self:
        self.chart = YamlCompressorChartBuilder().with_test_data().validate()
        self.control_margin = YamlControlMargin(unit=YamlControlMarginUnits.FRACTION, value=0.0)
        return self


# ---------------------------------------------------------------------------
# Process unit builders
# ---------------------------------------------------------------------------


class YamlCompressorBuilder(Builder[YamlCompressor]):
    def __init__(self):
        self.type = "COMPRESSOR"
        self.compressor_model = None

    def with_compressor_model(self, compressor_model: YamlCompressorModelChart) -> Self:
        self.compressor_model = compressor_model
        return self

    def with_test_data(self) -> Self:
        self.compressor_model = YamlCompressorModelChartBuilder().with_test_data().validate()
        return self


class YamlPressureDropperBuilder(Builder[YamlPressureDropper]):
    def __init__(self):
        self.type = "PRESSURE_DROPPER"
        self.pressure_drop = None

    def with_pressure_drop(self, pressure_drop: YamlExpressionType) -> Self:
        self.pressure_drop = pressure_drop
        return self

    def with_test_data(self) -> Self:
        self.pressure_drop = 1.0
        return self


class YamlTemperatureSetterBuilder(Builder[YamlTemperatureSetter]):
    def __init__(self):
        self.type = "TEMPERATURE_SETTER"
        self.temperature = None

    def with_temperature(self, temperature: YamlExpressionType) -> Self:
        self.temperature = temperature
        return self

    def with_test_data(self) -> Self:
        self.temperature = 30.0
        return self


class YamlLiquidRemoverBuilder(Builder[YamlLiquidRemover]):
    def __init__(self):
        self.type = "LIQUID_REMOVER"

    def with_test_data(self) -> Self:
        # LIQUID_REMOVER has no configurable fields beyond `type`,
        # so `with_test_data` is a no-op. Kept for API consistency
        # with the other process unit builders.
        return self


# ---------------------------------------------------------------------------
# Pipeline builder
# ---------------------------------------------------------------------------


class YamlProcessPipelineBuilder(Builder[YamlProcessPipeline]):
    def __init__(self):
        self.type = "SERIAL"
        self.name = None
        self.items = []

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_items(self, units: list[YamlProcessUnit]) -> Self:
        """Pass a list of validated process units (or string references).
        Each is wrapped in a YamlItem automatically."""
        self.items = [YamlItem(target=u) for u in units]
        return self

    def with_test_data(self) -> Self:
        self.name = "DefaultPipeline"
        self.items = [
            YamlItem(target=YamlPressureDropperBuilder().with_test_data().validate()),
            YamlItem(target=YamlTemperatureSetterBuilder().with_test_data().validate()),
            YamlItem(target=YamlLiquidRemoverBuilder().with_test_data().validate()),
            YamlItem(target=YamlCompressorBuilder().with_test_data().validate()),
        ]
        return self
