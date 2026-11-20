from typing import Self

from libecalc.common.utils.rates import RateType
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlCurve,
    YamlEfficiencyUnits,
    YamlHeadUnits,
    YamlRateUnits,
    YamlUnits,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import DefinitionReference, InstanceReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import YamlPressureDropperDefinition
from libecalc.presentation.yaml.yaml_types.pump.yaml_liquid_stream import (
    YamlLiquidInletStream,
    YamlLiquidStreamRate,
    YamlLiquidStreamRateUnit,
)
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_model import YamlPumpChart, YamlPumpModel
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_pipeline import (
    YamlPumpPipeline,
    YamlPumpPipelineUnit,
    YamlPumpProcessUnit,
)
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_simulation import (
    YamlPumpCommonStreamDistribution,
    YamlPumpCommonStreamSetting,
    YamlPumpConstraint,
    YamlPumpIndividualStreamDistribution,
    YamlPumpPressureControl,
    YamlPumpSimulation,
)
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile
from libecalc.presentation.yaml.yaml_types.yaml_pump import PumpReference, YamlPump
from libecalc.testing.process_builders import YamlPressureDropperBuilder
from libecalc.testing.yaml_builder import Builder

DEFAULT_PUMP_NAME = "default_pump"


class YamlPumpBuilder(Builder[YamlPump]):
    def __init__(self):
        self.name = None
        self.alias = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_alias(self, alias: str | None) -> Self:
        self.alias = alias
        return self

    def with_test_data(self) -> Self:
        self.name = DEFAULT_PUMP_NAME
        return self


class YamlPumpCurveBuilder(Builder[YamlCurve]):
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
        self.speed = 1.0
        self.rate = [277.0, 524.0, 666.0, 832.0, 927.0]
        self.head = [1062.0, 1004.0, 944.0, 847.0, 776.0]
        self.efficiency = [47.6, 64.3, 68.7, 70.5, 69.1]
        return self


class YamlPumpChartBuilder(Builder[YamlPumpChart]):
    def __init__(self):
        self.curves = None
        self.units = None

    def with_curves(self, curves: list[YamlCurve] | YamlFile) -> Self:
        self.curves = curves
        return self

    def with_units(self, units: YamlUnits) -> Self:
        self.units = units
        return self

    def with_test_data(self) -> Self:
        self.curves = [YamlPumpCurveBuilder().with_test_data().validate()]
        self.units = YamlUnits(
            rate=YamlRateUnits.AM3_PER_HOUR,
            head=YamlHeadUnits.M,
            efficiency=YamlEfficiencyUnits.PERCENTAGE,
        )
        return self


class YamlPumpModelBuilder(Builder[YamlPumpModel]):
    def __init__(self):
        self.type = "PUMP_CHART"
        self.chart = None
        self.minimum_flow_rate = None

    def with_chart(self, chart: YamlPumpChart) -> Self:
        self.chart = chart
        return self

    def with_minimum_flow_rate(self, minimum_flow_rate: float | None) -> Self:
        self.minimum_flow_rate = minimum_flow_rate
        return self

    def with_test_data(self) -> Self:
        self.chart = YamlPumpChartBuilder().with_test_data().validate()
        return self


class YamlPumpProcessUnitBuilder(Builder[YamlPumpProcessUnit]):
    def __init__(self):
        self.type = "PUMP"
        self.pump = None
        self.model = None

    def with_pump(self, pump: PumpReference) -> Self:
        self.pump = pump
        return self

    def with_model(self, model: YamlPumpModel | DefinitionReference) -> Self:
        self.model = model
        return self

    def with_test_data(self) -> Self:
        self.pump = DEFAULT_PUMP_NAME
        self.model = YamlPumpModelBuilder().with_test_data().validate()
        return self


class YamlPumpPipelineBuilder(Builder[YamlPumpPipeline]):
    def __init__(self):
        self.name = None
        self.process_units: list[YamlPumpPipelineUnit] = []

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_item(self, unit: YamlPumpPipelineUnit) -> Self:
        self.process_units.append(unit)
        return self

    def with_pressure_dropper_item(self, pressure_drop: YamlExpressionType) -> Self:
        dropper: YamlPressureDropperDefinition = (
            YamlPressureDropperBuilder().with_pressure_drop(pressure_drop).validate()
        )
        return self.with_item(dropper)

    def with_pump_item(self, pump: PumpReference, model: YamlPumpModel | DefinitionReference | None = None) -> Self:
        """Without a model, the pump gets the test data pump model in place."""
        if model is None:
            model = YamlPumpModelBuilder().with_test_data().validate()
        return self.with_item(YamlPumpProcessUnitBuilder().with_pump(pump).with_model(model).validate())

    def with_test_data(self) -> Self:
        self.name = "DefaultPumpPipeline"
        return self.with_pump_item(DEFAULT_PUMP_NAME)


class YamlLiquidStreamRateBuilder(Builder[YamlLiquidStreamRate]):
    def __init__(self):
        self.value = None
        self.unit = None
        self.type = None

    def with_value(self, value: YamlExpressionType) -> Self:
        self.value = value
        return self

    def with_unit(self, unit: YamlLiquidStreamRateUnit) -> Self:
        self.unit = unit
        return self

    def with_type(self, rate_type: RateType) -> Self:
        self.type = rate_type
        return self

    def with_test_data(self) -> Self:
        self.value = 12000.0
        self.unit = YamlLiquidStreamRateUnit.M3_PER_DAY
        self.type = RateType.STREAM_DAY
        return self


class YamlLiquidInletStreamBuilder(Builder[YamlLiquidInletStream]):
    def __init__(self):
        self.name = None
        self.pressure = None
        self.density = None
        self.rate = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_pressure(self, pressure: YamlExpressionType) -> Self:
        self.pressure = pressure
        return self

    def with_density(self, density: YamlExpressionType) -> Self:
        self.density = density
        return self

    def with_rate(self, rate: YamlLiquidStreamRate) -> Self:
        self.rate = rate
        return self

    def with_test_data(self) -> Self:
        self.name = "DefaultLiquidInletStream"
        self.pressure = 10.0
        self.density = 1022.0
        self.rate = YamlLiquidStreamRateBuilder().with_test_data().validate()
        return self


class YamlPumpCommonStreamDistributionBuilder(Builder[YamlPumpCommonStreamDistribution]):
    def __init__(self):
        self.method = "COMMON_STREAM"
        self.inlet_stream: YamlLiquidInletStream | None = None
        self.settings: list[YamlPumpCommonStreamSetting] = []

    def with_inlet_stream(self, inlet_stream: YamlLiquidInletStream) -> Self:
        self.inlet_stream = inlet_stream
        return self

    def with_settings(self, settings: list[YamlPumpCommonStreamSetting]) -> Self:
        self.settings = settings
        return self

    def with_rate_fractions(self, rate_fractions: list[list[YamlExpressionType]]) -> Self:
        self.settings = [YamlPumpCommonStreamSetting(rate_fractions=fractions) for fractions in rate_fractions]
        return self

    def with_test_data(self) -> Self:
        self.inlet_stream = YamlLiquidInletStreamBuilder().with_test_data().validate()
        self.settings = [YamlPumpCommonStreamSetting(rate_fractions=[1.0])]
        return self


class YamlPumpIndividualStreamDistributionBuilder(Builder[YamlPumpIndividualStreamDistribution]):
    def __init__(self):
        self.method = "INDIVIDUAL_STREAMS"
        self.inlet_streams: list[YamlLiquidInletStream] = []

    def with_inlet_streams(self, inlet_streams: list[YamlLiquidInletStream]) -> Self:
        self.inlet_streams = inlet_streams
        return self

    def with_test_data(self) -> Self:
        self.inlet_streams = [YamlLiquidInletStreamBuilder().with_test_data().validate()]
        return self


class YamlPumpConstraintBuilder(Builder[YamlPumpConstraint]):
    def __init__(self):
        self.process_unit = None
        self.outlet_pressure = None
        self.pressure_control = None

    def with_process_unit(self, process_unit: PumpReference | None) -> Self:
        self.process_unit = process_unit
        return self

    def with_outlet_pressure(self, outlet_pressure: YamlExpressionType) -> Self:
        self.outlet_pressure = outlet_pressure
        return self

    def with_pressure_control(self, pressure_control: YamlPumpPressureControl) -> Self:
        self.pressure_control = pressure_control
        return self

    def with_test_data(self) -> Self:
        self.outlet_pressure = 240.0
        self.pressure_control = YamlPumpPressureControl.NONE
        return self


class YamlPumpSimulationBuilder(Builder[YamlPumpSimulation]):
    def __init__(self):
        self.name: str | None = None
        self.targets: list[InstanceReference] = []
        self.stream_distribution = None
        self.constraints: dict[InstanceReference, list[YamlPumpConstraint]] = {}

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_target(self, target: InstanceReference) -> Self:
        self.targets.append(target)
        return self

    def with_stream_distribution(
        self, stream_distribution: YamlPumpCommonStreamDistribution | YamlPumpIndividualStreamDistribution
    ) -> Self:
        self.stream_distribution = stream_distribution
        return self

    def with_constraint(self, pipeline_name: InstanceReference, constraints: list[YamlPumpConstraint]) -> Self:
        self.constraints[pipeline_name] = constraints
        return self

    def with_pipeline(
        self,
        pipeline: YamlPumpPipeline,
        outlet_pressure: YamlExpressionType = 240.0,
        pressure_control: YamlPumpPressureControl = YamlPumpPressureControl.NONE,
    ) -> Self:
        self.targets.append(pipeline.name)
        self.constraints[pipeline.name] = [
            YamlPumpConstraintBuilder()
            .with_outlet_pressure(outlet_pressure)
            .with_pressure_control(pressure_control)
            .validate()
        ]
        return self

    def with_test_data(self) -> Self:
        self.name = "DefaultPumpSimulation"
        pipeline = YamlPumpPipelineBuilder().with_test_data().validate()
        self.with_pipeline(pipeline)
        self.stream_distribution = YamlPumpIndividualStreamDistributionBuilder().with_test_data().validate()
        return self
