from abc import ABC
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Literal, Optional, TypeVar, Union

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo
from typing_extensions import Annotated

from libecalc import dto
from libecalc.common.priorities import Priorities
from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.string.string_utils import generate_id, get_duplicates
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.dto.base import (
    Component,
    ComponentType,
    ConsumerUserDefinedCategoryType,
    EcalcBaseModel,
    InstallationUserDefinedCategoryType,
)
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.models import (
    ConsumerFunction,
    ElectricEnergyUsageModel,
    FuelEnergyUsageModel,
    GeneratorSetSampled,
)
from libecalc.dto.models.compressor import CompressorModel
from libecalc.dto.models.pump import PumpModel
from libecalc.dto.types import ConsumptionType, EnergyUsageType, FuelType
from libecalc.dto.utils.validators import (
    ComponentNameStr,
    ExpressionType,
    convert_expression,
    validate_temporal_model,
)
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)


def check_model_energy_usage_type(model_data: Dict[datetime, ConsumerFunction], energy_type: EnergyUsageType):
    for model in model_data.values():
        if model.energy_usage_type != energy_type:
            raise ValueError(f"Model does not consume {energy_type}")
    return model_data


class BaseComponent(Component, ABC):
    name: ComponentNameStr

    regularity: Dict[datetime, Expression]

    _validate_base_temporal_model = field_validator("regularity")(validate_temporal_model)


class BaseEquipment(BaseComponent, ABC):
    user_defined_category: Dict[datetime, ConsumerUserDefinedCategoryType] = Field(..., validate_default=True)

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @field_validator("user_defined_category", mode="before")
    def check_user_defined_category(cls, user_defined_category, info: ValidationInfo):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if isinstance(user_defined_category, dict) and len(user_defined_category.values()) > 0:
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
    fuel: Optional[Dict[datetime, FuelType]] = None

    @field_validator("fuel")
    @classmethod
    def validate_fuel_exist(cls, fuel, info: ValidationInfo):
        """
        Make sure fuel is set if consumption type is FUEL.
        """
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
    energy_usage_model: Dict[
        datetime,
        ElectricEnergyUsageModel,
    ]

    _validate_el_consumer_temporal_model = field_validator("energy_usage_model")(validate_temporal_model)

    _check_model_energy_usage = field_validator("energy_usage_model")(
        lambda data: check_model_energy_usage_type(data, EnergyUsageType.POWER)
    )


class FuelConsumer(BaseConsumer):
    component_type: Literal[
        ComponentType.COMPRESSOR,
        ComponentType.GENERIC,
        ComponentType.COMPRESSOR_SYSTEM,
    ]
    consumes: Literal[ConsumptionType.FUEL] = ConsumptionType.FUEL
    fuel: Dict[datetime, FuelType]
    energy_usage_model: Dict[datetime, FuelEnergyUsageModel]

    _validate_fuel_consumer_temporal_models = field_validator("energy_usage_model", "fuel")(validate_temporal_model)

    _check_model_energy_usage = field_validator("energy_usage_model")(
        lambda data: check_model_energy_usage_type(data, EnergyUsageType.FUEL)
    )


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
    energy_usage_model: Dict[datetime, CompressorModel]


class PumpComponent(BaseConsumer):
    component_type: Literal[ComponentType.PUMP] = ComponentType.PUMP
    energy_usage_model: Dict[datetime, PumpModel]


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
    stages: List[ConsumerComponent]
    streams: List[Stream]


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

SystemStreamConditions = Dict[ConsumerID, Dict[StreamID, ExpressionStreamConditions]]


class Crossover(EcalcBaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stream_name: Optional[str] = Field(None)
    from_component_id: str
    to_component_id: str


class SystemComponentConditions(EcalcBaseModel):
    crossover: List[Crossover]


class ConsumerSystem(BaseConsumer):
    component_type: Literal[ComponentType.CONSUMER_SYSTEM_V2] = Field(
        ComponentType.CONSUMER_SYSTEM_V2,
        title="TYPE",
        description="The type of the component",
    )
    component_conditions: SystemComponentConditions
    stream_conditions_priorities: Priorities[SystemStreamConditions]
    consumers: Union[List[CompressorComponent], List[PumpComponent]]

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for consumer in self.consumers:
            graph.add_node(consumer)
            graph.add_edge(self.id, consumer.id)
        return graph

    def evaluate_stream_conditions(
        self, variables_map: VariablesMap
    ) -> Priorities[Dict[ConsumerID, List[TimeSeriesStreamConditions]]]:
        parsed_priorities: Priorities[Dict[ConsumerID, List[TimeSeriesStreamConditions]]] = defaultdict(dict)
        for priority_name, priority in self.stream_conditions_priorities.items():
            for consumer_name, streams_conditions in priority.items():
                parsed_priorities[priority_name][generate_id(consumer_name)] = [
                    TimeSeriesStreamConditions(
                        id=generate_id(consumer_name, stream_name),
                        name="-".join([consumer_name, stream_name]),
                        rate=TimeSeriesStreamDayRate(
                            timesteps=variables_map.time_vector,
                            values=list(
                                Expression.setup_from_expression(stream_conditions.rate.value).evaluate(
                                    variables=variables_map.variables, fill_length=len(variables_map.time_vector)
                                )
                            ),
                            unit=stream_conditions.rate.unit,
                        )
                        if stream_conditions.rate is not None
                        else None,
                        pressure=TimeSeriesFloat(
                            timesteps=variables_map.time_vector,
                            values=list(
                                Expression.setup_from_expression(stream_conditions.pressure.value).evaluate(
                                    variables=variables_map.variables, fill_length=len(variables_map.time_vector)
                                )
                            ),
                            unit=stream_conditions.pressure.unit,
                        )
                        if stream_conditions.pressure is not None
                        else None,
                        fluid_density=TimeSeriesFloat(
                            timesteps=variables_map.time_vector,
                            values=list(
                                Expression.setup_from_expression(stream_conditions.fluid_density.value).evaluate(
                                    variables=variables_map.variables, fill_length=len(variables_map.time_vector)
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
    fuel: Dict[datetime, FuelType]
    generator_set_model: Dict[datetime, GeneratorSetSampled]
    consumers: List[
        Annotated[
            Union[ElectricityConsumer, ConsumerSystem],
            Field(discriminator="component_type"),
        ]
    ] = Field(default_factory=list)
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
    hydrocarbon_export: Dict[datetime, Expression]
    fuel_consumers: List[
        Annotated[
            Union[GeneratorSet, FuelConsumer, ConsumerSystem],
            Field(discriminator="component_type"),
        ]
    ] = Field(default_factory=list)
    venting_emitters: List[YamlVentingEmitter] = Field(default_factory=list)

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

    @field_validator("fuel_consumers", mode="before")
    def check_fuel_consumers_exist(cls, fuel_consumers):
        if not fuel_consumers:
            raise ValueError(
                f"Keywords are missing:\n It is required to specify at least one of the two keywords "
                f"{EcalcYamlKeywords.fuel_consumers} or {EcalcYamlKeywords.generator_sets} in the model.",
            )
        return fuel_consumers

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
    installations: List[Installation] = Field(default_factory=list)

    @property
    def installation_ids(self) -> List[str]:
        return [installation.id for installation in self.installations]

    def get_component_ids_for_installation_id(self, installation_id: str) -> List[str]:
        installation = self.get_installation(installation_id)
        component_ids = []
        for fuel_consumer in installation.fuel_consumers:
            component_ids.append(fuel_consumer.id)
            if isinstance(fuel_consumer, dto.GeneratorSet):
                for electricity_consumer in fuel_consumer.consumers:
                    component_ids.append(electricity_consumer.id)

        for emitter in installation.venting_emitters:
            component_ids.append(emitter.id)
        return component_ids

    def get_installation(self, installation_id: str) -> Installation:
        return next(installation for installation in self.installations if installation.id == installation_id)

    @model_validator(mode="after")
    def validate_unique_names(self):
        """Ensure unique component names within installation."""
        names = [self.name]
        fuel_types = [dto.FuelType]
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
