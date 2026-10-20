from typing import Self

from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlComponent,
    YamlCompressorSampled,
    YamlDieselConsumer,
    YamlDispatchStrategy,
    YamlDriveTrain,
    YamlElectricalBus,
    YamlElectricalCable,
    YamlElectricalConsumer,
    YamlElectricalMotor,
    YamlEnergyNetwork,
    YamlEnergySource,
    YamlEnergySourceType,
    YamlFuelGasConsumer,
    YamlFuelGasManifold,
    YamlGasTurbine,
    YamlGeneratorSet,
    YamlJunctionInput,
    YamlMechanicalConsumer,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import (
    YamlTurbineCurve,
    YamlTurbineDefinition,
)
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile
from libecalc.testing.yaml_builder import Builder

# ---------------------------------------------------------------------------
# Turbine definition builders
# ---------------------------------------------------------------------------


class YamlFileBuilder(Builder[YamlFile]):
    def __init__(self):
        self.file = None

    def with_file(self, file: str) -> Self:
        self.file = file
        return self

    def with_test_data(self) -> Self:
        self.file = "turbine_curve.csv"
        return self


class YamlTurbineCurveBuilder(Builder[YamlTurbineCurve]):
    def __init__(self):
        self.load = None
        self.efficiency = None

    def with_load(self, load: list[float]) -> Self:
        self.load = load
        return self

    def with_efficiency(self, efficiency: list[float]) -> Self:
        self.efficiency = efficiency
        return self

    def with_test_data(self) -> Self:
        self.load = [2.352, 4.589, 6.853]
        self.efficiency = [0.138, 0.210, 0.255]
        return self


class YamlTurbineDefinitionBuilder(Builder[YamlTurbineDefinition]):
    def __init__(self):
        self.lower_heating_value = None
        self.curve = None

    def with_lower_heating_value(self, lower_heating_value: float) -> Self:
        self.lower_heating_value = lower_heating_value
        return self

    def with_curve(self, curve: YamlTurbineCurve | YamlFile) -> Self:
        self.curve = curve
        return self

    def with_test_data(self) -> Self:
        self.lower_heating_value = 38.0
        self.curve = YamlTurbineCurveBuilder().with_test_data().validate()
        return self


# ---------------------------------------------------------------------------
# Source builders
# ---------------------------------------------------------------------------


class YamlEnergySourceBuilder(Builder[YamlEnergySource]):
    def __init__(self):
        self.name = None
        self.type = None
        self.capacity = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_type(self, type: YamlEnergySourceType) -> Self:
        self.type = type
        return self

    def with_capacity(self, capacity: YamlExpressionType) -> Self:
        self.capacity = capacity
        return self

    def with_test_data(self) -> Self:
        self.name = "fuel_gas"
        self.type = YamlEnergySourceType.FUEL_GAS_SOURCE
        return self


# ---------------------------------------------------------------------------
# Converter builders
# ---------------------------------------------------------------------------


class YamlEnergyGeneratorSetBuilder(Builder[YamlGeneratorSet]):
    def __init__(self):
        self.type = "GENERATOR_SET"
        self.name = None
        self.input = None
        self.capacity = None
        self.model = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: str) -> Self:
        self.input = input
        return self

    def with_capacity(self, capacity: YamlExpressionType) -> Self:
        self.capacity = capacity
        return self

    def with_model(self, model: str) -> Self:
        self.model = model
        return self

    def with_test_data(self) -> Self:
        self.name = "generator_set"
        self.input = "fuel_gas"
        self.capacity = 30
        self.model = "generator_set_model"
        return self


class YamlGasTurbineBuilder(Builder[YamlGasTurbine]):
    def __init__(self):
        self.type = "GAS_TURBINE"
        self.name = None
        self.input = None
        self.model = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: str) -> Self:
        self.input = input
        return self

    def with_model(self, model: YamlTurbineDefinition) -> Self:
        self.model = model
        return self

    def with_test_data(self) -> Self:
        self.name = "gas_turbine"
        self.input = "fuel_gas"
        self.model = YamlTurbineDefinitionBuilder().with_test_data().validate()
        return self


class YamlElectricalMotorBuilder(Builder[YamlElectricalMotor]):
    def __init__(self):
        self.type = "ELECTRICAL_MOTOR"
        self.name = None
        self.input = None
        self.capacity = None
        self.efficiency = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: str) -> Self:
        self.input = input
        return self

    def with_capacity(self, capacity: YamlExpressionType) -> Self:
        self.capacity = capacity
        return self

    def with_efficiency(self, efficiency: YamlExpressionType) -> Self:
        self.efficiency = efficiency
        return self

    def with_test_data(self) -> Self:
        self.name = "electrical_motor"
        self.input = "main_bus"
        self.efficiency = 0.95
        return self


class YamlElectricalCableBuilder(Builder[YamlElectricalCable]):
    def __init__(self):
        self.type = "ELECTRICAL_CABLE"
        self.name = None
        self.input = None
        self.capacity = None
        self.efficiency = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: str) -> Self:
        self.input = input
        return self

    def with_capacity(self, capacity: YamlExpressionType) -> Self:
        self.capacity = capacity
        return self

    def with_efficiency(self, efficiency: YamlExpressionType) -> Self:
        self.efficiency = efficiency
        return self

    def with_test_data(self) -> Self:
        self.name = "power_from_shore_cable"
        self.input = "power_from_shore"
        self.capacity = 20
        self.efficiency = 0.98
        return self


# ---------------------------------------------------------------------------
# Junction builders
# ---------------------------------------------------------------------------


class YamlElectricalBusBuilder(Builder[YamlElectricalBus]):
    def __init__(self):
        self.type = "ELECTRICAL_BUS"
        self.name = None
        self.input = None
        self.dispatch_strategy = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: list[str | YamlJunctionInput]) -> Self:
        self.input = input
        return self

    def with_dispatch_strategy(self, dispatch_strategy: YamlDispatchStrategy) -> Self:
        self.dispatch_strategy = dispatch_strategy
        return self

    def with_test_data(self) -> Self:
        self.name = "main_bus"
        self.input = [
            YamlJunctionInput(name="power_from_shore_cable", capacity=15),
            "generator_set",
        ]
        self.dispatch_strategy = YamlDispatchStrategy.PRIORITY
        return self


class YamlFuelGasManifoldBuilder(Builder[YamlFuelGasManifold]):
    def __init__(self):
        self.type = "FUEL_GAS_MANIFOLD"
        self.name = None
        self.input = None
        self.dispatch_strategy = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: list[str | YamlJunctionInput]) -> Self:
        self.input = input
        return self

    def with_dispatch_strategy(self, dispatch_strategy: YamlDispatchStrategy) -> Self:
        self.dispatch_strategy = dispatch_strategy
        return self

    def with_test_data(self) -> Self:
        self.name = "fuel_gas_manifold"
        self.input = ["fuel_gas", "imported_fuel_gas"]
        self.dispatch_strategy = YamlDispatchStrategy.PRIORITY
        return self


# ---------------------------------------------------------------------------
# Consumer builders
# ---------------------------------------------------------------------------


class YamlElectricalConsumerBuilder(Builder[YamlElectricalConsumer]):
    def __init__(self):
        self.type = "ELECTRICAL_CONSUMER"
        self.name = None
        self.input = None
        self.load = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: str) -> Self:
        self.input = input
        return self

    def with_load(self, load: YamlExpressionType) -> Self:
        self.load = load
        return self

    def with_test_data(self) -> Self:
        self.name = "base_load"
        self.input = "main_bus"
        self.load = 5
        return self


class YamlMechanicalConsumerBuilder(Builder[YamlMechanicalConsumer]):
    def __init__(self):
        self.type = "MECHANICAL_CONSUMER"
        self.name = None
        self.input = None
        self.load = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: str) -> Self:
        self.input = input
        return self

    def with_load(self, load: YamlExpressionType) -> Self:
        self.load = load
        return self

    def with_test_data(self) -> Self:
        self.name = "pump"
        self.input = "electrical_motor"
        self.load = 2
        return self


class YamlDriveTrainBuilder(Builder[YamlDriveTrain]):
    def __init__(self):
        self.type = "DRIVE_TRAIN"
        self.name = None
        self.input = None
        self.shaft = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: str) -> Self:
        self.input = input
        return self

    def with_shaft(self, shaft: str) -> Self:
        self.shaft = shaft
        return self

    def with_test_data(self) -> Self:
        self.name = "compressor_train"
        self.input = "gas_turbine"
        self.shaft = "default_shaft"
        return self


class YamlFuelGasConsumerBuilder(Builder[YamlFuelGasConsumer]):
    def __init__(self):
        self.type = "FUEL_GAS_CONSUMER"
        self.name = None
        self.input = None
        self.rate = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: str) -> Self:
        self.input = input
        return self

    def with_rate(self, rate: YamlExpressionType) -> Self:
        self.rate = rate
        return self

    def with_test_data(self) -> Self:
        self.name = "flare"
        self.input = "fuel_gas"
        self.rate = 10000
        return self


class YamlDieselConsumerBuilder(Builder[YamlDieselConsumer]):
    def __init__(self):
        self.type = "DIESEL_CONSUMER"
        self.name = None
        self.input = None
        self.rate = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: str) -> Self:
        self.input = input
        return self

    def with_rate(self, rate: YamlExpressionType) -> Self:
        self.rate = rate
        return self

    def with_test_data(self) -> Self:
        self.name = "diesel_engine"
        self.input = "diesel"
        self.rate = 5000
        return self


class YamlCompressorSampledBuilder(Builder[YamlCompressorSampled]):
    def __init__(self):
        self.type = "COMPRESSOR_SAMPLED"
        self.name = None
        self.input = None
        self.file = None
        self.rate = None
        self.suction_pressure = None
        self.discharge_pressure = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_input(self, input: str) -> Self:
        self.input = input
        return self

    def with_file(self, file: str) -> Self:
        self.file = file
        return self

    def with_rate(self, rate: YamlExpressionType) -> Self:
        self.rate = rate
        return self

    def with_suction_pressure(self, suction_pressure: YamlExpressionType) -> Self:
        self.suction_pressure = suction_pressure
        return self

    def with_discharge_pressure(self, discharge_pressure: YamlExpressionType) -> Self:
        self.discharge_pressure = discharge_pressure
        return self

    def with_test_data(self) -> Self:
        self.name = "gas_compressor_sampled"
        self.input = "fuel_gas"
        self.file = "gas_compressor_sampled.csv"
        self.rate = 2500000
        self.suction_pressure = 40
        self.discharge_pressure = 120
        return self


# ---------------------------------------------------------------------------
# Network builder
# ---------------------------------------------------------------------------


class YamlEnergyNetworkBuilder(Builder[YamlEnergyNetwork]):
    """
    Builder for ENERGY_NETWORK input
    """

    def __init__(self):
        self.sources: list[YamlEnergySource] = []
        self.units: list[YamlComponent] = []

    def with_test_data(self) -> Self:
        self.sources = [YamlEnergySourceBuilder().with_test_data().validate()]
        self.units = []
        return self

    def with_sources(self, sources: list[YamlEnergySource]) -> Self:
        self.sources = sources
        return self

    def with_units(self, units: list[YamlComponent]) -> Self:
        self.units = units
        return self

    def with_gas_turbine(self, name: str, input: str, model: YamlTurbineDefinition) -> Self:
        gas_turbine = YamlGasTurbineBuilder().with_name(name).with_input(input).with_model(model).validate()
        self.units = [*self.units, gas_turbine]
        return self

    def with_drive_train(self, name: str, input: str, shaft: str) -> Self:
        drive_train = YamlDriveTrainBuilder().with_name(name).with_input(input).with_shaft(shaft).validate()
        self.units = [*self.units, drive_train]
        return self
