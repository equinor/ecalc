import abc
from enum import Enum
from typing import Generic, Literal, Self, TypeVar, get_args

from typing_extensions import get_original_bases

from libecalc.common.utils.rates import RateType
from libecalc.dto.types import (
    ConsumerUserDefinedCategoryType,
    FuelTypeUserDefinedCategoryType,
    InstallationUserDefinedCategoryType,
)
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model import (
    YamlElectricityEnergyUsageModel,
    YamlEnergyUsageModelCompressor,
    YamlFuelEnergyUsageModel,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_direct import (
    ConsumptionRateType,
    YamlEnergyUsageModelDirect,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import YamlElectricityConsumer
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_fuel_consumer import YamlFuelConsumer
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import YamlGeneratorSet
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlDirectTypeEmitter,
    YamlOilTypeEmitter,
    YamlVentingEmission,
    YamlVentingEmitter,
    YamlVentingType,
    YamlVentingVolume,
    YamlVentingVolumeEmission,
)
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlCompressorTabularModel,
    YamlFacilityAdjustment,
    YamlFacilityModel,
    YamlFacilityModelType,
    YamlGeneratorSetModel,
)
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_emission import YamlEmission
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel, YamlTurbine
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    CompressorEnergyUsageModelModelReference,
    GeneratorSetModelReference,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import (
    YamlDefaultTimeSeriesCollection,
    YamlTimeSeriesCollection,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
    YamlEmissionRateUnits,
    YamlOilRateUnits,
    YamlOilVolumeRate,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariables

T = TypeVar("T")


class Builder(abc.ABC, Generic[T]):
    __model__: type[T]

    def __init_subclass__(cls, **kwargs):
        # When this class is subclassed we parse the type to be able to use the pydantic model for build and validate

        # Get the Builder[T] base from the subclass
        original_bases = list(get_original_bases(cls))
        assert len(original_bases) == 1
        original_base = original_bases[0]

        # Get the type of T in Builder[T], assuming a single class, i.e. no unions
        model_type: type[T] = list(get_args(original_base))[0]

        cls.__model__ = model_type

    @classmethod
    def get_model_fields(cls) -> list[str]:
        if "_fields_metadata" not in cls.__dict__:
            cls._fields_metadata = dict(cls.__model__.model_fields.items())

        return list(cls._fields_metadata.keys())

    @abc.abstractmethod
    def with_test_data(self) -> Self: ...

    def _get_model_data(self) -> dict:
        data = {}
        for attr in self.get_model_fields():
            if not hasattr(self, attr):
                continue

            value = getattr(self, attr)
            if isinstance(value, Enum):
                value = value.value

            if value is None:
                continue
            data[attr] = value
        return data

    def construct(self) -> T:
        return self.__model__.model_construct(_fields_set=None, **self._get_model_data())

    def validate(self) -> T:
        return self.__model__.model_validate(self._get_model_data())


class YamlTimeSeriesBuilder(Builder[YamlDefaultTimeSeriesCollection]):
    """
    Builder for TIME_SERIES input
    """

    def __init__(self):
        self.name = None
        self.type: Literal["DEFAULT", "MISCELLANEOUS"] = "DEFAULT"
        self.file = None
        self.influence_time_vector = True

    def with_name(self, name: str):
        self.name = name
        return self

    def with_type(self, type: str):
        self.type = type
        return self

    def with_file(self, file: str):
        self.file = file
        return self

    def with_test_data(self) -> Self:
        self.name = "DefaultTimeSeries"
        self.file = "DefaultTimeSeries.csv"
        return self


class YamlElectricity2fuelBuilder(Builder[YamlGeneratorSetModel]):
    """
    Builder for FACILITY_INPUTS of type ELECTRICITY2FUEL
    """

    def __init__(self):
        self.name = None
        self.file = None
        self.adjustment = None
        self.type = YamlFacilityModelType.ELECTRICITY2FUEL

    def with_name(self, name: str):
        self.name = name
        return self

    def with_file(self, file: str):
        self.file = file
        return self

    def with_adjustment(self, constant: float, factor: float):
        self.adjustment = YamlFacilityAdjustment(constant=constant, factor=factor)
        return self

    def with_test_data(self):
        self.adjustment = YamlFacilityAdjustment(constant=0, factor=1)
        self.name = "DefaultElectricity2fuel"
        self.file = "DefaultElectricity2fuel"
        return self


class YamlCompressorTabularBuilder(Builder[YamlCompressorTabularModel]):
    """
    Builder for FACILITY_INPUTS of type COMPRESSOR_TABULAR
    """

    def __init__(self):
        self.name = None
        self.file = None
        self.adjustment = None
        self.type = YamlFacilityModelType.COMPRESSOR_TABULAR

    def with_name(self, name: str):
        self.name = name
        return self

    def with_file(self, file: str):
        self.file = file
        return self

    def with_adjustment(self, constant: float, factor: float):
        self.adjustment = YamlFacilityAdjustment(constant=constant, factor=factor)
        return self

    def with_test_data(self):
        self.adjustment = YamlFacilityAdjustment(constant=0, factor=1)
        self.name = "DefaultElectricity2fuel"
        self.file = "electricity2fuel.csv"
        return self


class YamlEnergyUsageModelDirectBuilder(Builder[YamlEnergyUsageModelDirect]):
    def __init__(self):
        self.type = "DIRECT"
        self.load = None  # To be set with test data or custom value
        self.fuel_rate = None  # To be set with test data or custom value
        self.consumption_rate_type = None  # To be set with test data or custom value

    def with_test_data(self):
        self.load = None
        self.fuel_rate = "0.5"
        self.consumption_rate_type = ConsumptionRateType.STREAM_DAY.value
        return self

    def with_load(self, load: YamlExpressionType):
        self.load = load
        return self

    def with_fuel_rate(self, fuel_rate: YamlExpressionType):
        self.fuel_rate = fuel_rate
        return self

    def with_consumption_rate_type(self, consumption_rate_type: ConsumptionRateType):
        self.consumption_rate_type = consumption_rate_type.value
        return self


class YamlEnergyUsageModelCompressorBuilder(Builder[YamlEnergyUsageModelCompressor]):
    """
    Builder for compressor energy usage model
    """

    def __init__(self):
        self.type = "COMPRESSOR"
        self.energy_function = None
        self.rate = None
        self.suction_pressure = None
        self.discharge_pressure = None

    def with_energy_function(self, energy_function: CompressorEnergyUsageModelModelReference):
        self.energy_function = energy_function
        return self

    def with_rate(self, rate: YamlExpressionType):
        self.rate = rate
        return self

    def with_suction_pressure(self, suction_pressure: YamlExpressionType):
        self.suction_pressure = suction_pressure
        return self

    def with_discharge_pressure(self, discharge_pressure: YamlExpressionType):
        self.discharge_pressure = discharge_pressure
        return self

    def with_test_data(self):
        self.name = "CompressorDefault"
        self.rate = 10
        self.energy_function = YamlCompressorTabularBuilder().with_test_data().validate().name
        self.suction_pressure = 20
        self.discharge_pressure = 80


TYamlClass = TypeVar("TYamlClass", bound=YamlBase)


class YamlFuelConsumerBuilder(Builder[YamlFuelConsumer]):
    def __init__(self):
        self.name = None
        self.fuel = None
        self.energy_usage_model = None
        self.category = None

    def with_test_data(self) -> Self:
        self.name = "flare"
        self.category = ConsumerUserDefinedCategoryType.FLARE.value
        self.energy_usage_model = YamlEnergyUsageModelDirectBuilder().with_test_data().validate()
        self.fuel = YamlFuelTypeBuilder().with_test_data().validate().name
        return self

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_fuel(self, fuel: YamlTemporalModel[str]):
        self.fuel = fuel
        return self

    def with_category(self, category: YamlTemporalModel[ConsumerUserDefinedCategoryType]):
        self.category = category
        return self

    def with_energy_usage_model(self, energy_usage_model: YamlTemporalModel[YamlFuelEnergyUsageModel]) -> Self:
        self.energy_usage_model = energy_usage_model
        return self


class YamlElectricityConsumerBuilder(Builder[YamlElectricityConsumer]):
    """
    Builder for electricity consumer
    """

    def __init__(self):
        self.name = None
        self.energy_usage_model = None
        self.category = None

    def with_test_data(self) -> Self:
        self.name = "base load"
        self.category = ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD.value
        self.energy_usage_model = (
            YamlEnergyUsageModelDirectBuilder().with_test_data().with_load("0.5").with_fuel_rate(None).validate()
        )
        return self

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_category(self, category: YamlTemporalModel[ConsumerUserDefinedCategoryType]) -> Self:
        self.category = category
        return self

    def with_energy_usage_model(self, energy_usage_model: YamlTemporalModel[YamlElectricityEnergyUsageModel]) -> Self:
        self.energy_usage_model = energy_usage_model
        return self


class YamlGeneratorSetBuilder(Builder[YamlGeneratorSet]):
    """
    Builder for generator set
    """

    def __init__(self):
        self.name = None
        self.category = None
        self.fuel = None
        self.electricity2fuel = None
        self.cable_loss = None
        self.max_usage_from_shore = None
        self.consumers = []

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_category(self, category: YamlTemporalModel[ConsumerUserDefinedCategoryType]) -> Self:
        self.category = category
        return self

    def with_fuel(self, fuel: YamlTemporalModel[str]) -> Self:
        self.fuel = fuel
        return self

    def with_electricity2fuel(self, electricity2fuel: YamlTemporalModel[GeneratorSetModelReference]) -> Self:
        self.electricity2fuel = electricity2fuel
        return self

    def with_consumers(self, consumers: list[YamlElectricityConsumer]) -> Self:
        self.consumers = consumers
        return self

    def with_cable_loss(self, cable_loss: YamlExpressionType) -> Self:
        self.cable_loss = cable_loss
        return self

    def with_max_usage_from_shore(self, max_usage_from_shore: YamlExpressionType) -> Self:
        self.max_usage_from_shore = max_usage_from_shore
        return self

    def with_test_data(self) -> Self:
        self.name = "DefaultGeneratorSet"
        self.category = ConsumerUserDefinedCategoryType.TURBINE_GENERATOR
        self.fuel = YamlFuelTypeBuilder().with_test_data().validate().name
        self.electricity2fuel = YamlElectricity2fuelBuilder().with_test_data().validate().name
        self.consumers = [YamlElectricityConsumerBuilder().with_test_data().validate()]

        return self


class YamlVentingEmitterDirectTypeBuilder(Builder[YamlDirectTypeEmitter]):
    """
    Builder for venting emitter of type DIRECT_EMISSION
    """

    def __init__(self):
        self.name = None
        self.category = None
        self.type = YamlVentingType.DIRECT_EMISSION
        self.emissions = []

    def with_test_data(self) -> Self:
        self.name = "VentingEmitterDirectTypeDefault"
        self.category = ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE
        self.emissions.append(YamlVentingEmissionBuilder().with_test_data().validate())
        return self

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_category(self, category: ConsumerUserDefinedCategoryType) -> Self:
        self.category = category
        return self

    def with_emissions(self, emissions: list[YamlVentingEmission]) -> Self:
        self.emissions = emissions
        return self

    def with_emission_names_and_rates(self, names: list[str], rates: list[YamlExpressionType]) -> Self:
        for name, rate in zip(names, rates):
            self.emissions.append(YamlVentingEmissionBuilder().with_name(name).with_rate(rate).validate())
        return self

    def with_emission_names_rates_units_and_types(
        self,
        names: list[str],
        rates: list[YamlExpressionType],
        units: list[YamlEmissionRateUnits],
        rate_types: list[RateType],
    ) -> Self:
        for name, rate, unit, rate_type in zip(names, rates, units, rate_types):
            self.emissions.append(
                YamlVentingEmissionBuilder()
                .with_name(name)
                .with_rate(YamlEmissionRateBuilder().with_value(rate).with_type(rate_type).with_unit(unit).validate())
                .validate()
            )

        return self


class YamlVentingEmitterOilTypeBuilder(Builder[YamlOilTypeEmitter]):
    """
    Builder for venting emitter of type OIL_VOLUME
    """

    def __init__(self):
        self.name = None
        self.category = None
        self.type = YamlVentingType.OIL_VOLUME
        self.volume = None

    def with_test_data(self) -> Self:
        self.name = "VentingEmitterOilTypeDefault"
        self.category = ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE
        self.volume = YamlVentingVolumeBuilder().with_test_data().validate()

        return self

    def with_rate_and_emission_names_and_factors(
        self,
        rate: YamlExpressionType,
        names: list[str],
        factors: list[YamlExpressionType],
        unit: YamlOilRateUnits = YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY,
        rate_type: RateType = RateType.STREAM_DAY,
    ) -> Self:
        self.volume = (
            YamlVentingVolumeBuilder()
            .with_rate(YamlOilVolumeRateBuilder().with_value(rate).with_unit(unit).with_type(rate_type).validate())
            .with_emissions(
                [YamlVentingVolumeEmission(name=name, emission_factor=factor) for name, factor in zip(names, factors)]
            )
            .validate()
        )

        return self

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_category(self, category: ConsumerUserDefinedCategoryType) -> Self:
        self.category = category
        return self

    def with_volume(self, volume: YamlVentingVolume) -> Self:
        self.volume = volume
        return self


class YamlVentingEmissionBuilder(Builder[YamlVentingEmission]):
    """
    Builder for venting emission
    """

    def __init__(self):
        self.name = None
        self.rate = None

    def with_test_data(self) -> Self:
        self.name = "VentingEmissionDefault"
        self.rate = YamlEmissionRateBuilder().with_test_data().validate()
        return self

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_rate(self, rate: YamlEmissionRate) -> Self:
        self.rate = rate
        return self


class YamlVentingVolumeBuilder(Builder[YamlVentingVolume]):
    """
    Builder for YamlVentingVolume
    """

    def __init__(self):
        self.rate = None
        self.emissions = []

    def with_test_data(self) -> Self:
        self.rate = YamlOilVolumeRateBuilder().with_test_data().validate()
        self.emissions = [
            YamlVentingVolumeEmission(name="co2", emission_factor=2),
        ]
        return self

    def with_rate(self, rate: YamlOilVolumeRate) -> Self:
        self.rate = rate
        return self

    def with_emissions(self, emissions: list[YamlVentingVolumeEmission]) -> Self:
        self.emissions = emissions
        return self

    def with_emission_names_and_factors(self, names: list[str], factors: list[YamlExpressionType]) -> Self:
        self.emissions = [
            YamlVentingVolumeEmission(name=name, emission_factor=factor) for name, factor in zip(names, factors)
        ]
        return self


class YamlEmissionRateBuilder(Builder[YamlEmissionRate]):
    """
    Builder for emission rate
    """

    def __init__(self):
        self.value = None
        self.unit = None
        self.type = None
        self.condition = None
        self.conditions = None

    def with_test_data(self) -> Self:
        self.value = 10
        self.unit = YamlEmissionRateUnits.KILO_PER_DAY
        self.type = RateType.STREAM_DAY
        return self

    def with_value(self, value: YamlExpressionType) -> Self:
        self.value = value
        return self

    def with_unit(self, unit: YamlEmissionRateUnits) -> Self:
        self.unit = unit
        return self

    def with_type(self, rate_type: RateType) -> Self:
        self.type = rate_type
        return self

    def with_condition(self, condition: str) -> Self:
        self.condition = condition
        return self

    def with_conditions(self, conditions: list[str]) -> Self:
        self.conditions = conditions
        return self


class YamlOilVolumeRateBuilder(Builder[YamlOilVolumeRate]):
    """
    Builder for oil volume rate
    """

    def __init__(self):
        self.value = None
        self.unit = None
        self.type = None
        self.condition = None
        self.conditions = None

    def with_test_data(self) -> Self:
        self.value = 10
        self.unit = YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY
        self.type = RateType.STREAM_DAY
        return self

    def with_value(self, value: YamlExpressionType) -> Self:
        self.value = value
        return self

    def with_unit(self, unit: YamlOilRateUnits) -> Self:
        self.unit = unit
        return self

    def with_type(self, rate_type: RateType) -> Self:
        self.type = rate_type
        return self

    def with_condition(self, condition: str) -> Self:
        self.condition = condition
        return self

    def with_conditions(self, conditions: list[str]) -> Self:
        self.conditions = conditions
        return self


class YamlInstallationBuilder(Builder[YamlInstallation]):
    def __init__(self):
        self.name = None
        self.category = None
        self.hydrocarbon_export = None
        self.fuel = None
        self.regularity = None
        self.generator_sets = []
        self.fuel_consumers = []
        self.venting_emitters = []

        self._yaml_model_containers = []

    def with_category(self, category: InstallationUserDefinedCategoryType) -> Self:
        self.category = category
        return self

    def with_regularity(self, regularity: YamlTemporalModel[YamlExpressionType]) -> Self:
        self.regularity = regularity
        return self

    def with_fuel(self, fuel=YamlTemporalModel[str]):
        self.fuel = fuel
        return self

    def with_test_data(self):
        self.name = "DefaultInstallation"
        self.hydrocarbon_export = 0
        self.regularity = 1
        self.fuel_consumers = [YamlFuelConsumerBuilder().with_test_data().validate()]
        return self

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_fuel_consumers(self, fuel_consumers: list[YamlFuelConsumer]) -> Self:
        new_fuel_consumers = []
        for fuel_consumer in fuel_consumers:
            new_fuel_consumers.append(fuel_consumer)
        self.fuel_consumers = new_fuel_consumers
        return self

    def with_venting_emitters(self, venting_emitters: list[YamlVentingEmitter]) -> Self:
        new_venting_emitters = []
        for venting_emitter in venting_emitters:
            new_venting_emitters.append(venting_emitter)
        self.venting_emitters = new_venting_emitters
        return self

    def with_generator_sets(self, generator_sets: list[YamlGeneratorSet]) -> Self:
        new_generator_sets = []
        for generator_set in generator_sets:
            new_generator_sets.append(generator_set)
        self.generator_sets = new_generator_sets
        return self


class YamlEmissionBuilder(Builder[YamlEmission]):
    def __init__(self):
        self.name = None
        self.factor = None

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_factor(self, factor: YamlExpressionType) -> Self:
        self.factor = factor
        return self

    def with_test_data(self) -> Self:
        self.name = "CO2"
        self.factor = 2
        return self


class YamlFuelTypeBuilder(Builder[YamlFuelType]):
    def __init__(self):
        self.name = None
        self.category = None
        self.emissions = []

    def with_test_data(self) -> Self:
        self.name = "fuel"
        emission_builder = YamlEmissionBuilder().with_test_data()
        self.emissions.append(emission_builder.validate())
        return self

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_emissions(self, emissions: list[YamlEmission]) -> Self:
        self.emissions = emissions
        return self

    def with_category(self, category: FuelTypeUserDefinedCategoryType) -> Self:
        self.category = category
        return self

    def with_emission_names_and_factors(self, names: list[str], factors: list[YamlExpressionType]) -> Self:
        for name, factor in zip(names, factors):
            self.emissions.append(YamlEmissionBuilder().with_name(name).with_factor(factor).validate())
        return self


class YamlAssetBuilder(Builder[YamlAsset]):
    def __init__(self):
        self.time_series = []
        self.facility_inputs = []
        self.models = []
        self.fuel_types = []
        self.variables = None
        self.installations = []
        self.start = None
        self.end = None

    def with_test_data(self):
        self.time_series = []

        self.facility_inputs = []

        self.models = []

        # Create and populate a list of YamlFuelType test instances
        fuel_types_builder = YamlFuelTypeBuilder().with_test_data()
        self.fuel_types = [fuel_types_builder.validate()]

        self.variables = None

        # Create and populate a list of YamlInstallation test instances
        installations_builder = YamlInstallationBuilder().with_test_data()
        self.installations = [installations_builder.validate()]

        self.start = "2019-01-01"
        self.end = "2024-01-01"

        return self

    def with_time_series(self, time_series: list[YamlTimeSeriesCollection]):
        self.time_series = time_series
        return self

    def with_facility_inputs(self, facility_inputs: list[YamlFacilityModel]):
        self.facility_inputs = facility_inputs
        return self

    def with_models(self, models: list[YamlConsumerModel]):
        self.models = models
        return self

    def with_fuel_types(self, fuel_types: list[YamlFuelType]):
        self.fuel_types = fuel_types
        return self

    def with_variables(self, variables: YamlVariables):
        self.variables = variables
        return self

    def with_installations(self, installations: list[YamlInstallation]):
        if len(installations) == 0:
            self.installations = []
            return self

        new_installations = []
        for installation in installations:
            new_installations.append(installation)

        self.installations = new_installations
        return self

    def with_start(self, start: str):
        self.start = start
        return self

    def with_end(self, end: str):
        self.end = end
        return self


class YamlTurbineBuilder(Builder[YamlTurbine]):
    def __init__(self):
        self.name = None
        self.type = YamlModelType.TURBINE
        self.lower_heating_value = None
        self.turbine_loads = []
        self.turbine_efficiencies = []
        self.power_adjustment_constant = 0
        self.power_adjustment_factor = 1.0

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_lower_heating_value(self, lower_heating_value: float) -> Self:
        self.lower_heating_value = lower_heating_value
        return self

    def with_turbine_loads(self, turbine_loads: list[float]) -> Self:
        self.turbine_loads = turbine_loads
        return self

    def with_turbine_efficiencies(self, turbine_efficiencies: list[float]) -> Self:
        self.turbine_efficiencies = turbine_efficiencies
        return self

    def with_power_adjustment_constant(self, power_adjustment_constant: float) -> Self:
        self.power_adjustment_constant = power_adjustment_constant
        return self

    def with_power_adjustment_factor(self, power_adjustment_factor: float) -> Self:
        self.power_adjustment_factor = power_adjustment_factor
        return self

    def with_test_data(self) -> Self:
        self.name = "compressor_train_turbine"
        self.lower_heating_value = 38
        self.turbine_loads = [0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767]
        self.turbine_efficiencies = [0, 0.138, 0.210, 0.255, 0.286, 0.310, 0.328, 0.342, 0.353, 0.360, 0.362]

        return self
