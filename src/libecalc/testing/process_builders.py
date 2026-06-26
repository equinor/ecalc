from typing import Self, Literal

from libecalc.common.utils.rates import RateType
from libecalc.presentation.yaml.yaml_types.models import YamlFluidModel
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import (
    YamlEosModel,
    YamlPredefinedFluidType,
    YamlFluidModelType,
    YamlPredefinedFluidModel,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import ProcessUnitReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import (
    YamlProcessConstraint,
    YamlProcessSimulation,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_stream_distribution import (
    YamlCommonStreamDistribution,
    YamlIndividualStreamDistribution,
    YamlCommonStreamSetting,
    YamlOverflow,
)
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import (
    YamlInletStreamRate,
    YamlInletStream,
    YamlStreamRateUnit,
)
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType
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
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    YamlItem,
    YamlProcessPipeline,
)

from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlLiquidRemover,
    YamlTemperatureSetter,
    YamlPressureDropper,
    YamlCompressorModelChart,
    YamlCompressor,
    YamlControlMargin,
    YamlCompressorChart,
    YamlProcessUnit,
    YamlMixer,
    YamlSplitter,
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
        self.rate = [500.0, 3000.0, 5000.0, 8000.0]
        self.head = [30000.0, 25000.0, 20000.0, 15000.0]
        self.efficiency = [0.68, 0.72, 0.74, 0.70]
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
            efficiency=YamlEfficiencyUnits.FRACTION,
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


class YamlMixerBuilder(Builder[YamlMixer]):
    def __init__(self):
        self.type = "MIXER"
        self.sidestream = None

    def with_sidestream(self, sidestream: str | YamlInletStream) -> Self:
        self.sidestream = sidestream
        return self

    def with_test_data(self) -> Self:
        self.sidestream = (
            YamlInletStreamBuilder()
            .with_test_data()
            .with_name("SidestreamDefault")
            .with_rate(YamlInletStreamRateBuilder().with_test_data().with_value(200000).validate())
            .validate()
        )
        return self


class YamlSplitterBuilder(Builder[YamlSplitter]):
    def __init__(self):
        self.type = "SPLITTER"
        self.offtake_rate = None

    def with_offtake_rate(self, offtake_rate: YamlInletStreamRate) -> Self:
        self.offtake_rate = offtake_rate
        return self

    def with_test_data(self) -> Self:
        self.offtake_rate = YamlInletStreamRateBuilder().with_test_data().with_value(50_000).validate()
        return self


# ---------------------------------------------------------------------------
# Pipeline builder
# ---------------------------------------------------------------------------


class YamlProcessPipelineBuilder(Builder[YamlProcessPipeline]):
    def __init__(self):
        self.type = "SERIAL"
        self.name = None
        self.items = []
        self.anti_surge = "INDIVIDUAL_ASV"

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_item(self, target: YamlProcessUnit | ProcessUnitReference, name: str | None = None) -> Self:
        self.items.append(YamlItem(name=name, target=target))
        return self

    def with_items(self, items: list[tuple[str | None, YamlProcessUnit | ProcessUnitReference]]) -> Self:
        """Pass a list of validated process units (or string references).
        Each is wrapped in a YamlItem automatically."""
        for name, target in items:
            self.with_item(name=name, target=target)
        return self

    def with_anti_surge(self, anti_surge: str) -> Self:
        self.anti_surge = anti_surge
        return self

    def with_test_data(self) -> Self:
        self.name = "DefaultPipeline"
        (
            self.with_item(
                name="default_pressure_dropper", target=YamlPressureDropperBuilder().with_test_data().validate()
            ),
        )
        (
            self.with_item(
                name="default_temperature_setter", target=YamlTemperatureSetterBuilder().with_test_data().validate()
            ),
        )
        (self.with_item(name="default_liquid_remover", target=YamlLiquidRemoverBuilder().with_test_data().validate()),)
        (self.with_item(name="default_compressor", target=YamlCompressorBuilder().with_test_data().validate()),)
        return self


# ---------------------------------------------------------------------------
# Fluid model builders
# ---------------------------------------------------------------------------


class YamlPredefinedFluidModelBuilder(Builder[YamlPredefinedFluidModel]):
    def __init__(self):
        self.name = None
        self.type = YamlModelType.FLUID
        self.fluid_model_type = YamlFluidModelType.PREDEFINED
        self.eos_model = None
        self.gas_type = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_eos_model(self, eos_model: YamlEosModel) -> Self:
        self.eos_model = eos_model
        return self

    def with_gas_type(self, gas_type: YamlPredefinedFluidType) -> Self:
        self.gas_type = gas_type
        return self

    def with_test_data(self) -> Self:
        self.name = "DefaultFluidModel"
        self.eos_model = YamlEosModel.SRK
        self.gas_type = YamlPredefinedFluidType.MEDIUM
        return self


# ---------------------------------------------------------------------------
# Inlet stream builders
# ---------------------------------------------------------------------------


class YamlInletStreamRateBuilder(Builder[YamlInletStreamRate]):
    def __init__(self):
        self.value = None
        self.unit = None
        self.type = None

    def with_value(self, value: YamlExpressionType) -> Self:
        self.value = value
        return self

    def with_unit(self, unit: YamlStreamRateUnit) -> Self:
        self.unit = unit
        return self

    def with_type(self, rate_type: RateType) -> Self:
        self.type = rate_type
        return self

    def with_test_data(self) -> Self:
        self.value = 1000000.0
        self.unit = YamlStreamRateUnit.SM3_PER_DAY
        self.type = RateType.STREAM_DAY
        return self


class YamlInletStreamBuilder(Builder[YamlInletStream]):
    def __init__(self):
        self.name = None
        self.fluid_model = None
        self.pressure = None
        self.temperature = None
        self.rate = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_fluid_model(self, fluid_model: str | YamlFluidModel) -> Self:
        self.fluid_model = fluid_model
        return self

    def with_pressure(self, pressure: YamlExpressionType) -> Self:
        self.pressure = pressure
        return self

    def with_temperature(self, temperature: YamlExpressionType) -> Self:
        self.temperature = temperature
        return self

    def with_rate(self, rate: YamlInletStreamRate) -> Self:
        self.rate = rate
        return self

    def with_test_data(self) -> Self:
        self.name = "DefaultInletStream"
        self.fluid_model = YamlPredefinedFluidModelBuilder().with_test_data().validate()
        self.pressure = 20.0
        self.temperature = 30.0
        self.rate = YamlInletStreamRateBuilder().with_test_data().validate()
        return self


# ---------------------------------------------------------------------------
# Stream distribution builders
# ---------------------------------------------------------------------------


class YamlIndividualStreamDistributionBuilder(Builder[YamlIndividualStreamDistribution]):
    def __init__(self):
        self.method = "INDIVIDUAL_STREAMS"
        self.inlet_streams: list[str | YamlInletStream] = []

    def with_inlet_streams(self, inlet_streams: list[str | YamlInletStream]) -> Self:
        self.inlet_streams = inlet_streams
        return self

    def with_test_data(self) -> Self:
        self.inlet_streams = [YamlInletStreamBuilder().with_test_data().validate()]
        return self


class YamlCommonStreamDistributionBuilder(Builder[YamlCommonStreamDistribution]):
    def __init__(self):
        self.method = "COMMON_STREAM"
        self.inlet_stream: str | YamlInletStream | None = None
        self.settings: list[YamlCommonStreamSetting] = []

    def with_inlet_stream(self, inlet_stream: str | YamlInletStream) -> Self:
        self.inlet_stream = inlet_stream
        return self

    def with_settings(self, settings: list[YamlCommonStreamSetting]) -> Self:
        self.settings = settings
        return self

    def with_rate_fractions(
        self,
        rate_fractions: list[YamlExpressionType],
        overflow: list[YamlOverflow] | None = None,
    ) -> Self:
        self.settings = [YamlCommonStreamSetting(rate_fractions=rate_fractions, overflow=overflow)]
        return self

    def with_test_data(self) -> Self:
        self.inlet_stream = YamlInletStreamBuilder().with_test_data().validate()
        self.settings = [YamlCommonStreamSetting(rate_fractions=[1.0], overflow=None)]
        return self


# ---------------------------------------------------------------------------
# Process simulation builder
# ---------------------------------------------------------------------------


class YamlProcessSimulationBuilder(Builder[YamlProcessSimulation]):
    def __init__(self):
        self.name: str | None = None
        self.targets: list[YamlItem[YamlProcessPipeline]] = []
        self.stream_distribution = None
        self.constraints: dict[str, list[YamlProcessConstraint]] = {}

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_stream_distribution(
        self,
        stream_distribution: YamlCommonStreamDistribution | YamlIndividualStreamDistribution,
    ) -> Self:
        self.stream_distribution = stream_distribution
        return self

    def with_pipeline(
        self,
        pipeline: YamlProcessPipeline,
        pressure_control: PressureControlType = "DOWNSTREAM_CHOKE",
        anti_surge: AntiSurgeType = AntiSurgeType.INDIVIDUAL_ASV,
        outlet_pressure: YamlExpressionType = 100.0,
    ) -> Self:
        self.targets.append(YamlItem(target=pipeline))
        self.constraints[pipeline.name] = [
            YamlProcessConstraint(
                process_unit=pipeline.items[-1].name,
                outlet_pressure=outlet_pressure,
                pressure_control=pressure_control,
                anti_surge=anti_surge,
            )
        ]
        return self

    def with_test_data(self) -> Self:
        self.name = "DefaultProcessSimulation"
        pipeline = YamlProcessPipelineBuilder().with_test_data().with_name("DefaultPipeline").validate()
        self.with_pipeline(pipeline)
        self.stream_distribution = YamlIndividualStreamDistributionBuilder().with_test_data().validate()
        return self
