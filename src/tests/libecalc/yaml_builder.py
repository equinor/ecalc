import abc
from enum import Enum
from typing import List, Self, TypeVar, Generic, Any

from pydantic import TypeAdapter

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
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
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
    @abc.abstractmethod
    def with_test_data(self) -> Self: ...

    @abc.abstractmethod
    def build(self) -> T: ...


TClass = TypeVar("TClass", bound=YamlBase)


def _build(obj: Any, attrs: list[str], c: type[TClass], exclude_none=True):
    data = {}
    for attr in attrs:
        value = getattr(obj, attr)
        if isinstance(value, Enum):
            value = value.value

        if value is None:
            continue
        data[attr] = value

    return TypeAdapter(c).validate_python(data)


class YamlEnergyUsageModelDirectBuilder:
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

    def build(self) -> YamlEnergyUsageModelDirect:
        return _build(self, ["type", "load", "fuel_rate", "consumption_rate_type"], YamlEnergyUsageModelDirect)


TYamlClass = TypeVar("TYamlClass", bound=YamlBase)


class YamlModelContainer(Generic[TYamlClass]):
    """
    Consumer, Installation wrapper that can be used to bundle the component with its dependencies.

    A fuel consumer that uses a model reference can then use this class to keep the referenced model in a single class.
    """

    def __init__(self, component: TYamlClass):
        self.component = component
        self.models = None
        self.time_series = None
        self.facility_inputs = None

    def with_models(self, models) -> Self:
        self.models = models
        return self

    def with_time_series(self, time_series):
        self.time_series = time_series
        return self

    def with_facility_inputs(self, facility_inputs) -> Self:
        self.facility_inputs = facility_inputs
        return self


class YamlFuelConsumerBuilder:
    def __init__(self):
        self.name = None
        self.fuel = None
        self.energy_usage_model = None
        self.category = None

    def with_test_data(self) -> Self:
        self.name = "flare"
        self.category = ConsumerUserDefinedCategoryType.FLARE.value
        self.energy_usage_model = YamlEnergyUsageModelDirectBuilder().with_test_data().build()
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

    def build(self) -> YamlFuelConsumer:
        return _build(self, ["name", "category", "fuel", "energy_usage_model"], YamlFuelConsumer)


class YamlInstallationBuilder:
    def __init__(self):
        self.name = None
        self.category = None  # Placeholder for InstallationUserDefinedCategoryType
        self.hydrocarbon_export = None  # Placeholder for YamlTemporalModel[YamlExpressionType]
        self.fuel = None  # Placeholder for YamlTemporalModel[str]
        self.regularity = None  # Placeholder for YamlTemporalModel[YamlExpressionType]
        self.generator_sets = []  # Placeholder for List[YamlGeneratorSet]
        self.fuel_consumers = []  # Placeholder for List[Union[YamlFuelConsumer, YamlConsumerSystem]]
        self.venting_emitters = []  # Placeholder for List[YamlVentingEmitter]

        self._yaml_model_containers = []

    def with_test_data(self):
        # Populate with test data if needed
        # For example, create a list of YamlGeneratorSet, YamlFuelConsumer, YamlConsumerSystem, and YamlVentingEmitter instances
        # self.generator_sets.append(YamlGeneratorSetBuilder().with_test_data().build())
        # self.fuel_consumers.append(YamlFuelConsumerBuilder().with_test_data().build())
        # self.venting_emitters.append(YamlVentingEmitterBuilder().with_test_data().build())
        self.name = "DefaultInstallation"
        self.hydrocarbon_export = 0
        self.regularity = 1
        self.fuel_consumers.append(YamlFuelConsumerBuilder().with_test_data().build())
        return self

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def with_fuel_consumers(
        self, fuel_consumers: list[YamlFuelConsumer | YamlModelContainer[YamlFuelConsumer]]
    ) -> Self:
        new_fuel_consumers = []
        for fuel_consumer in fuel_consumers:
            if isinstance(fuel_consumer, YamlModelContainer):
                self._yaml_model_containers.append(fuel_consumer)
                new_fuel_consumers.append(fuel_consumer.component)
            else:
                new_fuel_consumers.append(fuel_consumer)
        self.fuel_consumers = new_fuel_consumers
        return self

    def build(self) -> YamlInstallation:
        return _build(
            self,
            [
                "name",
                "category",
                "fuel",
                "hydrocarbon_export",
                "regularity",
                "generator_sets",
                "fuel_consumers",
                "venting_emitters",
            ],
            YamlInstallation,
        )


class YamlEmissionBuilder:
    def __init__(self):
        self.name = None
        self.factor = None

    def with_test_data(self) -> Self:
        # Populate with test data if needed
        self.name = "CO2"
        self.factor = 2
        return self

    def build(self) -> YamlEmission:
        return _build(self, ["name", "factor"], YamlEmission)


# Builder for YamlFuelType
class YamlFuelTypeBuilder:
    def __init__(self):
        self.name = None
        self.category = None  # Placeholder for FuelTypeUserDefinedCategoryType
        self.emissions = []  # Placeholder for a list of YamlEmission

    def with_test_data(self) -> Self:
        # Populate with test data if needed
        # For example, create a list of YamlEmission instances using YamlEmissionBuilder
        self.name = "fuel"
        emission_builder = YamlEmissionBuilder().with_test_data()
        self.emissions.append(emission_builder.build())
        return self

    def with_name(self, name: str) -> Self:
        self.name = name
        return self

    def build(self) -> YamlFuelType:
        return _build(self, ["name", "category", "emissions"], YamlFuelType)


class YamlAssetBuilder:
    def __init__(self):
        self.time_series = []
        self.facility_inputs = []
        self.models = []
        self.fuel_types = []
        self.variables = None
        self.installations = []
        self.start = None
        self.end = None

    def with_test_data(self, fuel_name: str = "fuel"):
        self.time_series = []

        self.facility_inputs = []

        self.models = []

        # Create and populate a list of YamlFuelType test instances
        fuel_types_builder = YamlFuelTypeBuilder().with_test_data().with_name(fuel_name)
        self.fuel_types = [fuel_types_builder.build()]

        self.variables = None

        # Create and populate a list of YamlInstallation test instances
        installations_builder = YamlInstallationBuilder().with_test_data()
        self.installations = [installations_builder.build()]

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

    def with_installations(self, installations: List[YamlInstallation | YamlModelContainer[YamlInstallation]]):
        if len(installations) == 0:
            self.installations = []
            return self

        new_installations = []
        for installation in installations:
            if isinstance(installation, YamlModelContainer):
                self.models.extend(installation.models)
                self.facility_inputs.extend(installation.facility_inputs)
                self.time_series.extend(installation.time_series)
                new_installations.append(installation.component)
            else:
                new_installations.append(installation)

        self.installations = new_installations
        return self

    def with_start(self, start: str):
        self.start = start
        return self

    def with_end(self, end: str):
        self.end = end
        return self

    def build(self) -> YamlAsset:
        return _build(
            self,
            ["time_series", "facility_inputs", "models", "fuel_types", "variables", "installations", "start", "end"],
            YamlAsset,
        )
