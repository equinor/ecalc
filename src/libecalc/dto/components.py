from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from typing import Annotated, Any, Literal, Optional, TypeVar, Union

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.priorities import Priorities
from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.string.string_utils import generate_id, get_duplicates
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.dto.base import (
    EcalcBaseModel,
)
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.fuel_type import FuelType
from libecalc.dto.models import (
    ConsumerFunction,
    ElectricEnergyUsageModel,
    FuelEnergyUsageModel,
    GeneratorSetSampled,
)
from libecalc.dto.models.compressor import CompressorModel
from libecalc.dto.models.pump import PumpModel
from libecalc.dto.types import ConsumerUserDefinedCategoryType, InstallationUserDefinedCategoryType
from libecalc.dto.utils.validators import (
    ComponentNameStr,
    ExpressionType,
    convert_expression,
    validate_temporal_model,
)
from libecalc.expression import Expression
from libecalc.presentation.yaml.ltp_validation import (
    validate_generator_set_power_from_shore,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)


def check_model_energy_usage_type(model_data: dict[Period, ConsumerFunction], energy_type: EnergyUsageType):
    for model in model_data.values():
        if model.energy_usage_type != energy_type:
            raise ValueError(f"Model does not consume {energy_type.value}")
    return model_data


class Component(EcalcBaseModel, ABC):
    component_type: ComponentType

    @property
    @abstractmethod
    def id(self) -> str: ...


class BaseComponent(Component, ABC):
    name: ComponentNameStr

    regularity: dict[Period, Expression]

    _validate_base_temporal_model = field_validator("regularity")(validate_temporal_model)

    @field_validator("regularity", mode="before")
    @classmethod
    def check_regularity(cls, regularity):
        if isinstance(regularity, dict) and len(regularity.values()) > 0:
            regularity = _convert_keys_in_dictionary_from_str_to_periods(regularity)
        return regularity


class BaseEquipment(BaseComponent, ABC):
    user_defined_category: dict[Period, ConsumerUserDefinedCategoryType] = Field(..., validate_default=True)

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @field_validator("user_defined_category", mode="before")
    def check_user_defined_category(cls, user_defined_category, info: ValidationInfo):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if isinstance(user_defined_category, dict) and len(user_defined_category.values()) > 0:
            user_defined_category = _convert_keys_in_dictionary_from_str_to_periods(user_defined_category)
            for user_category in user_defined_category.values():
                if user_category not in list(ConsumerUserDefinedCategoryType):
                    name_context_str = ""
                    if (name := info.data.get("name")) is not None:
                        name_context_str = f"with the name {name}"

                    raise ValueError(
                        f"CATEGORY: {user_category} is not allowed for {cls.__name__} {name_context_str}. Valid categories are: {[(consumer_user_defined_category.value) for consumer_user_defined_category in ConsumerUserDefinedCategoryType]}"
                    )

        return user_defined_category


class BaseConsumer(BaseEquipment, ABC):
    """Base class for all consumers."""

    consumes: ConsumptionType
    fuel: Optional[dict[Period, FuelType]] = None

    @field_validator("fuel", mode="before")
    @classmethod
    def validate_fuel_exist(cls, fuel, info: ValidationInfo):
        """
        Make sure fuel is set if consumption type is FUEL.
        """
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        if info.data.get("consumes") == ConsumptionType.FUEL and (fuel is None or len(fuel) < 1):
            msg = f"Missing fuel for fuel consumer '{info.data.get('name')}'"
            raise ValueError(msg)
        return fuel


class ElectricityConsumer(BaseConsumer):
    component_type: Literal[
        ComponentType.COMPRESSOR,
        ComponentType.PUMP,
        ComponentType.GENERIC,
        ComponentType.PUMP_SYSTEM,
        ComponentType.COMPRESSOR_SYSTEM,
    ]
    consumes: Literal[ConsumptionType.ELECTRICITY] = ConsumptionType.ELECTRICITY
    energy_usage_model: dict[
        Period,
        ElectricEnergyUsageModel,
    ]

    _validate_el_consumer_temporal_model = field_validator("energy_usage_model")(validate_temporal_model)

    _check_model_energy_usage = field_validator("energy_usage_model")(
        lambda data: check_model_energy_usage_type(data, EnergyUsageType.POWER)
    )

    @field_validator("energy_usage_model", mode="before")
    @classmethod
    def check_energy_usage_model(cls, energy_usage_model):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(energy_usage_model, dict) and len(energy_usage_model.values()) > 0:
            energy_usage_model = _convert_keys_in_dictionary_from_str_to_periods(energy_usage_model)
        return energy_usage_model


class FuelConsumer(BaseConsumer):
    component_type: Literal[
        ComponentType.COMPRESSOR,
        ComponentType.GENERIC,
        ComponentType.COMPRESSOR_SYSTEM,
    ]
    consumes: Literal[ConsumptionType.FUEL] = ConsumptionType.FUEL
    fuel: dict[Period, FuelType]
    energy_usage_model: dict[Period, FuelEnergyUsageModel]

    _validate_fuel_consumer_temporal_models = field_validator("energy_usage_model", "fuel")(validate_temporal_model)

    _check_model_energy_usage = field_validator("energy_usage_model")(
        lambda data: check_model_energy_usage_type(data, EnergyUsageType.FUEL)
    )

    @field_validator("energy_usage_model", mode="before")
    @classmethod
    def check_energy_usage_model(cls, energy_usage_model, info: ValidationInfo):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(energy_usage_model, dict) and len(energy_usage_model.values()) > 0:
            energy_usage_model = _convert_keys_in_dictionary_from_str_to_periods(energy_usage_model)
        return energy_usage_model

    @field_validator("fuel", mode="before")
    @classmethod
    def check_fuel(cls, fuel):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        return fuel


Consumer = Annotated[Union[FuelConsumer, ElectricityConsumer], Field(discriminator="consumes")]


class CompressorOperationalSettings(EcalcBaseModel):
    rate: Expression
    inlet_pressure: Expression
    outlet_pressure: Expression


class PumpOperationalSettings(EcalcBaseModel):
    rate: Expression
    inlet_pressure: Expression
    outlet_pressure: Expression
    fluid_density: Expression


class CompressorComponent(BaseConsumer):
    component_type: Literal[ComponentType.COMPRESSOR] = ComponentType.COMPRESSOR
    energy_usage_model: dict[Period, CompressorModel]


class PumpComponent(BaseConsumer):
    component_type: Literal[ComponentType.PUMP] = ComponentType.PUMP
    energy_usage_model: dict[Period, PumpModel]


class Stream(EcalcBaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stream_name: Optional[str] = Field(None)
    from_component_id: str
    to_component_id: str


ConsumerComponent = TypeVar("ConsumerComponent", bound=Union[CompressorComponent, PumpComponent])


class TrainComponent(BaseConsumer):
    component_type: Literal[ComponentType.TRAIN_V2] = Field(
        ComponentType.TRAIN_V2,
        title="TYPE",
        description="The type of the component",
        alias="TYPE",
    )
    stages: list[ConsumerComponent]
    streams: list[Stream]


class ExpressionTimeSeries(EcalcBaseModel):
    value: ExpressionType
    unit: Unit
    type: Optional[RateType] = None


class ExpressionStreamConditions(EcalcBaseModel):
    rate: Optional[ExpressionTimeSeries] = None
    pressure: Optional[ExpressionTimeSeries] = None
    temperature: Optional[ExpressionTimeSeries] = None
    fluid_density: Optional[ExpressionTimeSeries] = None


ConsumerID = str
PriorityID = str
StreamID = str

SystemStreamConditions = dict[ConsumerID, dict[StreamID, ExpressionStreamConditions]]


class Crossover(EcalcBaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stream_name: Optional[str] = Field(None)
    from_component_id: str
    to_component_id: str


class SystemComponentConditions(EcalcBaseModel):
    crossover: list[Crossover]


class ConsumerSystem(BaseConsumer):
    component_type: Literal[ComponentType.CONSUMER_SYSTEM_V2] = Field(
        ComponentType.CONSUMER_SYSTEM_V2,
        title="TYPE",
        description="The type of the component",
    )
    component_conditions: SystemComponentConditions
    stream_conditions_priorities: Priorities[SystemStreamConditions]
    consumers: Union[list[CompressorComponent], list[PumpComponent]]

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for consumer in self.consumers:
            graph.add_node(consumer)
            graph.add_edge(self.id, consumer.id)
        return graph

    def evaluate_stream_conditions(
        self, expression_evaluator: ExpressionEvaluator
    ) -> Priorities[dict[ConsumerID, list[TimeSeriesStreamConditions]]]:
        parsed_priorities: Priorities[dict[ConsumerID, list[TimeSeriesStreamConditions]]] = defaultdict(dict)
        for priority_name, priority in self.stream_conditions_priorities.items():
            for consumer_name, streams_conditions in priority.items():
                parsed_priorities[priority_name][generate_id(consumer_name)] = [
                    TimeSeriesStreamConditions(
                        id=generate_id(consumer_name, stream_name),
                        name="-".join([consumer_name, stream_name]),
                        rate=TimeSeriesStreamDayRate(
                            periods=expression_evaluator.get_periods(),
                            values=list(
                                expression_evaluator.evaluate(
                                    Expression.setup_from_expression(stream_conditions.rate.value)
                                )
                            ),
                            unit=stream_conditions.rate.unit,
                        )
                        if stream_conditions.rate is not None
                        else None,
                        pressure=TimeSeriesFloat(
                            periods=expression_evaluator.get_periods(),
                            values=list(
                                expression_evaluator.evaluate(
                                    expression=Expression.setup_from_expression(stream_conditions.pressure.value)
                                )
                            ),
                            unit=stream_conditions.pressure.unit,
                        )
                        if stream_conditions.pressure is not None
                        else None,
                        fluid_density=TimeSeriesFloat(
                            periods=expression_evaluator.get_periods(),
                            values=list(
                                expression_evaluator.evaluate(
                                    expression=Expression.setup_from_expression(stream_conditions.fluid_density.value)
                                )
                            ),
                            unit=stream_conditions.fluid_density.unit,
                        )
                        if stream_conditions.fluid_density is not None
                        else None,
                    )
                    for stream_name, stream_conditions in streams_conditions.items()
                ]
        return dict(parsed_priorities)


class GeneratorSet(BaseEquipment):
    component_type: Literal[ComponentType.GENERATOR_SET] = ComponentType.GENERATOR_SET
    fuel: dict[Period, FuelType]
    generator_set_model: dict[Period, GeneratorSetSampled]
    consumers: list[
        Annotated[
            Union[ElectricityConsumer, ConsumerSystem],
            Field(discriminator="component_type"),
        ]
    ] = Field(default_factory=list)
    cable_loss: Optional[ExpressionType] = Field(
        None,
        title="CABLE_LOSS",
        description="Power loss in cables from shore. " "Used to calculate onshore delivery/power supply onshore.",
    )
    max_usage_from_shore: Optional[ExpressionType] = Field(
        None, title="MAX_USAGE_FROM_SHORE", description="The peak load/effect that is expected for one hour, per year."
    )
    _validate_genset_temporal_models = field_validator("generator_set_model", "fuel")(validate_temporal_model)

    @field_validator("user_defined_category", mode="before")
    @classmethod
    def check_mandatory_category_for_generator_set(cls, user_defined_category, info: ValidationInfo):
        """This could be handled automatically with Pydantic, but I want to inform the users in a better way, in
        particular since we introduced a breaking change for this to be mandatory for GeneratorSets in v7.2.
        """
        if user_defined_category is None or user_defined_category == "":
            raise ValueError(f"CATEGORY is mandatory and must be set for '{info.data.get('name', cls.__name__)}'")

        return user_defined_category

    @field_validator("generator_set_model", mode="before")
    @classmethod
    def check_generator_set_model(cls, generator_set_model, info: ValidationInfo):
        if isinstance(generator_set_model, dict) and len(generator_set_model.values()) > 0:
            generator_set_model = _convert_keys_in_dictionary_from_str_to_periods(generator_set_model)
        return generator_set_model

    @field_validator("fuel", mode="before")
    @classmethod
    def check_fuel(cls, fuel, info: ValidationInfo):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        return fuel

    @model_validator(mode="after")
    def check_power_from_shore(self):
        _check_power_from_shore_attributes = validate_generator_set_power_from_shore(
            cable_loss=self.cable_loss,
            max_usage_from_shore=self.max_usage_from_shore,
            model_fields=self.model_fields,
            category=self.user_defined_category,
        )

        return self

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for electricity_consumer in self.consumers:
            if hasattr(electricity_consumer, "get_graph"):
                graph.add_subgraph(electricity_consumer.get_graph())
            else:
                graph.add_node(electricity_consumer)

            graph.add_edge(self.id, electricity_consumer.id)

        return graph


class Installation(BaseComponent):
    component_type: Literal[ComponentType.INSTALLATION] = ComponentType.INSTALLATION
    user_defined_category: Optional[InstallationUserDefinedCategoryType] = Field(default=None, validate_default=True)
    hydrocarbon_export: dict[Period, Expression]
    fuel_consumers: list[
        Annotated[
            Union[GeneratorSet, FuelConsumer, ConsumerSystem],
            Field(discriminator="component_type"),
        ]
    ] = Field(default_factory=list)
    venting_emitters: list[YamlVentingEmitter] = Field(default_factory=list)

    @property
    def id(self) -> str:
        return generate_id(self.name)

    _validate_installation_temporal_model = field_validator("hydrocarbon_export")(validate_temporal_model)

    _convert_expression_installation = field_validator("regularity", "hydrocarbon_export", mode="before")(
        convert_expression
    )

    @field_validator("user_defined_category", mode="before")
    def check_user_defined_category(cls, user_defined_category, info: ValidationInfo):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if user_defined_category is not None:
            if user_defined_category not in list(InstallationUserDefinedCategoryType):
                name_context_str = ""
                if (name := info.data.get("name")) is not None:
                    name_context_str = f"with the name {name}"

                raise ValueError(
                    f"CATEGORY: {user_defined_category} is not allowed for {cls.__name__} {name_context_str}. Valid categories are: {[str(installation_user_defined_category.value) for installation_user_defined_category in InstallationUserDefinedCategoryType]}"
                )

        return user_defined_category

    @model_validator(mode="after")
    def check_fuel_consumers_or_venting_emitters_exist(self):
        try:
            if self.fuel_consumers or self.venting_emitters or self.generator_sets:
                return self
        except AttributeError:
            raise ValueError(
                f"Keywords are missing:\n It is required to specify at least one of the keywords "
                f"{EcalcYamlKeywords.fuel_consumers}, {EcalcYamlKeywords.generator_sets} or {EcalcYamlKeywords.installation_venting_emitters} in the model.",
            ) from None

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for component in [*self.fuel_consumers, *self.venting_emitters]:
            if hasattr(component, "get_graph"):
                graph.add_subgraph(component.get_graph())
            else:
                graph.add_node(component)

            graph.add_edge(self.id, component.id)

        return graph


class Asset(Component):
    @property
    def id(self):
        return generate_id(self.name)

    component_type: Literal[ComponentType.ASSET] = ComponentType.ASSET

    name: ComponentNameStr
    installations: list[Installation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_names(self):
        """Ensure unique component names within installation."""
        names = [self.name]
        fuel_types = [FuelType]
        fuel_names = [str]
        for installation in self.installations:
            names.append(installation.name)
            fuel_consumers = installation.fuel_consumers
            venting_emitters = installation.venting_emitters

            names.extend([venting_emitter.name for venting_emitter in venting_emitters])
            for fuel_consumer in fuel_consumers:
                names.append(fuel_consumer.name)
                if isinstance(fuel_consumer, GeneratorSet):
                    for electricity_consumer in fuel_consumer.consumers:
                        if isinstance(electricity_consumer, ConsumerSystem):
                            for consumer in electricity_consumer.consumers:
                                names.append(consumer.name)
                elif isinstance(fuel_consumer, ConsumerSystem):
                    for consumer in fuel_consumer.consumers:
                        names.append(consumer.name)
                if fuel_consumer.fuel is not None:
                    for fuel_type in fuel_consumer.fuel.values():
                        # Need to verify that it is a different fuel
                        if fuel_type is not None and fuel_type not in fuel_types:
                            fuel_types.append(fuel_type)
                            fuel_names.append(fuel_type.name)

        duplicated_names = get_duplicates(names)
        duplicated_fuel_names = get_duplicates(fuel_names)

        if len(duplicated_names) > 0:
            raise ValueError(
                "Component names must be unique. Components include the main model, installations,"
                " generator sets, electricity consumers, fuel consumers, systems and its consumers and direct emitters."
                f" Duplicated names are: {', '.join(duplicated_names)}"
            )

        if len(duplicated_fuel_names) > 0:
            raise ValueError(
                "Fuel type names must be unique across installations."
                f" Duplicated names are: {', '.join(duplicated_fuel_names)}"
            )
        return self

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for installation in self.installations:
            graph.add_subgraph(installation.get_graph())
            graph.add_edge(self.id, installation.id)

        return graph


ComponentDTO = Union[
    Asset,
    Installation,
    GeneratorSet,
    FuelConsumer,
    ElectricityConsumer,
    ConsumerSystem,
    CompressorComponent,
    PumpComponent,
]


def _convert_keys_in_dictionary_from_str_to_periods(data: dict[Union[str, Period], Any]) -> dict[Period, Any]:
    if all(isinstance(key, str) for key in data.keys()):
        return {
            Period(
                start=datetime.strptime(period.split(";")[0], "%Y-%m-%d %H:%M:%S"),
                end=datetime.strptime(period.split(";")[1], "%Y-%m-%d %H:%M:%S"),
            ): value
            for period, value in data.items()
        }
    else:
        return data
