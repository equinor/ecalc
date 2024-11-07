import abc
from enum import Enum
from typing import List, Self, TypeVar, Generic, get_args, cast

from typing_extensions import get_original_bases

from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model import YamlFuelEnergyUsageModel
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_direct import (
    ConsumptionRateType,
    YamlEnergyUsageModelDirect,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_fuel_consumer import YamlFuelConsumer
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import YamlGeneratorSet
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import YamlVentingEmitter
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlFacilityModel,
)
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_emission import YamlEmission
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import (
    YamlTimeSeriesCollection,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariables

T = TypeVar("T")


class Builder(abc.ABC, Generic[T]):
    __model__: type[T]

    def __init_subclass__(cls, **kwargs):
        # When this class is subclassed we parse the type to be able to use the pydantic model for build and validate

        # Get the Builder[T] base from the subclass
        original_bases = [base for base in get_original_bases(cls)]
        assert len(original_bases) == 1
        original_base = original_bases[0]

        # Get the type of T in Builder[T], assuming a single class, i.e. no unions
        model_type: type[T] = [arg for arg in get_args(original_base)][0]

        cls.__model__ = model_type

    @classmethod
    def get_model_fields(cls) -> list[str]:
        if "_fields_metadata" not in cls.__dict__:
            cls._fields_metadata = {
                field_name: field_info for field_name, field_info in cls.__model__.model_fields.items()
            }

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
        self.fuel = None
        return self

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_fuel(self, fuel: str) -> Self:
        self.fuel = fuel
        return self

    def with_energy_usage_model(self, energy_usage_model: YamlTemporalModel[YamlFuelEnergyUsageModel]) -> Self:
        self.energy_usage_model = energy_usage_model
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

    def with_test_data(self):
        self.name = "DefaultInstallation"
        self.hydrocarbon_export = 0
        self.regularity = 1
        self.fuel_consumers.append(YamlFuelConsumerBuilder().with_test_data().validate())
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

    def with_time_series(self, time_series: List[YamlTimeSeriesCollection]):
        self.time_series = time_series
        return self

    def with_facility_inputs(self, facility_inputs: List[YamlFacilityModel]):
        self.facility_inputs = facility_inputs
        return self

    def with_models(self, models: List[YamlConsumerModel]):
        self.models = models
        return self

    def with_fuel_types(self, fuel_types: List[YamlFuelType]):
        self.fuel_types = fuel_types
        return self

    def with_variables(self, variables: YamlVariables):
        self.variables = variables
        return self

    def with_installations(self, installations: List[YamlInstallation]):
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
