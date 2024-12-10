from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from typing import Annotated, Any, Literal, Optional, TypeVar, Union, overload

import numpy as np
from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.application.energy.component_energy_context import ComponentEnergyContext
from libecalc.application.energy.emitter import Emitter
from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.application.energy.energy_model import EnergyModel
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.logger import logger
from libecalc.common.priorities import Priorities
from libecalc.common.priority_optimizer import PriorityOptimizer
from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.string.string_utils import generate_id, get_duplicates
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.string.string_utils import generate_id
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesStreamDayRate,
    TimeSeriesString,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.models.compressor import create_compressor_model
from libecalc.core.models.generator import GeneratorModelSampled
from libecalc.core.models.pump import create_pump_model
from libecalc.core.result import ComponentResult, EcalcModelResult
from libecalc.core.result.emission import EmissionResult
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
from libecalc.infrastructure.energy_components.compressor import Compressor
from libecalc.infrastructure.energy_components.consumer_system import ConsumerSystem as ConsumerSystemEnergyComponent
from libecalc.infrastructure.energy_components.generator_set.generator_set import Genset
from libecalc.infrastructure.energy_components.legacy_consumer.component import Consumer as ConsumerEnergyComponent
from libecalc.infrastructure.energy_components.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.infrastructure.energy_components.pump import Pump
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


class ElectricityConsumer(BaseConsumer, EnergyComponent):
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

    def is_fuel_consumer(self) -> bool:
        return False

    def is_electricity_consumer(self) -> bool:
        return True

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def evaluate_energy_usage(
        self, expression_evaluator: ExpressionEvaluator, context: ComponentEnergyContext
    ) -> dict[str, EcalcModelResult]:
        consumer_results: dict[str, EcalcModelResult] = {}
        consumer = ConsumerEnergyComponent(
            id=self.id,
            name=self.name,
            component_type=self.component_type,
            regularity=TemporalModel(self.regularity),
            consumes=self.consumes,
            energy_usage_model=TemporalModel(
                {
                    period: EnergyModelMapper.from_dto_to_domain(model)
                    for period, model in self.energy_usage_model.items()
                }
            ),
        )
        consumer_results[self.id] = consumer.evaluate(expression_evaluator=expression_evaluator)

        return consumer_results

    @field_validator("energy_usage_model", mode="before")
    @classmethod
    def check_energy_usage_model(cls, energy_usage_model):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(energy_usage_model, dict) and len(energy_usage_model.values()) > 0:
            energy_usage_model = _convert_keys_in_dictionary_from_str_to_periods(energy_usage_model)
        return energy_usage_model


class FuelConsumer(BaseConsumer, Emitter, EnergyComponent):
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

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        return False

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def evaluate_energy_usage(
        self, expression_evaluator: ExpressionEvaluator, context: ComponentEnergyContext
    ) -> dict[str, EcalcModelResult]:
        consumer_results: dict[str, EcalcModelResult] = {}
        consumer = ConsumerEnergyComponent(
            id=self.id,
            name=self.name,
            component_type=self.component_type,
            regularity=TemporalModel(self.regularity),
            consumes=self.consumes,
            energy_usage_model=TemporalModel(
                {
                    period: EnergyModelMapper.from_dto_to_domain(model)
                    for period, model in self.energy_usage_model.items()
                }
            ),
        )
        consumer_results[self.id] = consumer.evaluate(expression_evaluator=expression_evaluator)

        return consumer_results

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
        expression_evaluator: ExpressionEvaluator,
    ) -> Optional[dict[str, EmissionResult]]:
        fuel_model = FuelModel(self.fuel)
        fuel_usage = energy_context.get_fuel_usage()

        assert fuel_usage is not None

        return fuel_model.evaluate_emissions(
            expression_evaluator=expression_evaluator,
            fuel_rate=fuel_usage.values,
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


class CompressorComponent(BaseConsumer, EnergyComponent):
    component_type: Literal[ComponentType.COMPRESSOR] = ComponentType.COMPRESSOR
    energy_usage_model: dict[Period, CompressorModel]

    def is_fuel_consumer(self) -> bool:
        return self.consumes == ConsumptionType.FUEL

    def is_electricity_consumer(self) -> bool:
        return self.consumes == ConsumptionType.ELECTRICITY

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name


class PumpComponent(BaseConsumer, EnergyComponent):
    component_type: Literal[ComponentType.PUMP] = ComponentType.PUMP
    energy_usage_model: dict[Period, PumpModel]

    def is_fuel_consumer(self) -> bool:
        return self.consumes == ConsumptionType.FUEL

    def is_electricity_consumer(self) -> bool:
        return self.consumes == ConsumptionType.ELECTRICITY

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name


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


class ConsumerSystem(BaseConsumer, Emitter, EnergyComponent):
    component_type: Literal[ComponentType.CONSUMER_SYSTEM_V2] = Field(
        ComponentType.CONSUMER_SYSTEM_V2,
        title="TYPE",
        description="The type of the component",
    )

    component_conditions: SystemComponentConditions
    stream_conditions_priorities: Priorities[SystemStreamConditions]
    consumers: Union[list[CompressorComponent], list[PumpComponent]]

    def is_fuel_consumer(self) -> bool:
        return self.consumes == ConsumptionType.FUEL

    def is_electricity_consumer(self) -> bool:
        return self.consumes == ConsumptionType.ELECTRICITY

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return True

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def evaluate_energy_usage(
        self, expression_evaluator: ExpressionEvaluator, context: ComponentEnergyContext
    ) -> dict[str, EcalcModelResult]:
        consumer_results = {}
        evaluated_stream_conditions = self.evaluate_stream_conditions(
            expression_evaluator=expression_evaluator,
        )
        optimizer = PriorityOptimizer()

        results_per_period: dict[str, dict[Period, ComponentResult]] = defaultdict(dict)
        priorities_used = []
        for period in expression_evaluator.get_periods():
            consumers_for_period = [
                create_consumer(
                    consumer=consumer,
                    period=period,
                )
                for consumer in self.consumers
            ]

            consumer_system = ConsumerSystemEnergyComponent(
                id=self.id,
                consumers=consumers_for_period,
                component_conditions=self.component_conditions,
            )

            def evaluator(priority: PriorityID):
                stream_conditions_for_priority = evaluated_stream_conditions[priority]
                stream_conditions_for_timestep = {
                    component_id: [stream_condition.for_period(period) for stream_condition in stream_conditions]
                    for component_id, stream_conditions in stream_conditions_for_priority.items()
                }
                return consumer_system.evaluate_consumers(stream_conditions_for_timestep)

            optimizer_result = optimizer.optimize(
                priorities=list(evaluated_stream_conditions.keys()),
                evaluator=evaluator,
            )
            priorities_used.append(optimizer_result.priority_used)
            for consumer_result in optimizer_result.priority_results:
                results_per_period[consumer_result.id][period] = consumer_result

        priorities_used = TimeSeriesString(
            periods=expression_evaluator.get_periods(),
            values=priorities_used,
            unit=Unit.NONE,
        )
        # merge consumer results
        consumer_ids = [consumer.id for consumer in self.consumers]
        merged_consumer_results = []
        for consumer_id in consumer_ids:
            first_result, *rest_results = list(results_per_period[consumer_id].values())
            merged_consumer_results.append(first_result.merge(*rest_results))

        # Convert to legacy compatible operational_settings_used
        priorities_to_int_map = {
            priority_name: index + 1 for index, priority_name in enumerate(evaluated_stream_conditions.keys())
        }
        operational_settings_used = TimeSeriesInt(
            periods=priorities_used.periods,
            values=[priorities_to_int_map[priority_name] for priority_name in priorities_used.values],
            unit=priorities_used.unit,
        )

        system_result = ConsumerSystemEnergyComponent.get_system_result(
            id=self.id,
            consumer_results=merged_consumer_results,
            operational_settings_used=operational_settings_used,
        )
        consumer_results[self.id] = system_result
        for consumer_result in merged_consumer_results:
            consumer_results[consumer_result.id] = EcalcModelResult(
                component_result=consumer_result,
                sub_components=[],
                models=[],
            )

        return consumer_results

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
        expression_evaluator: ExpressionEvaluator,
    ) -> Optional[dict[str, EmissionResult]]:
        if self.is_fuel_consumer():
            assert self.fuel is not None
            fuel_model = FuelModel(self.fuel)
            fuel_usage = energy_context.get_fuel_usage()

            assert fuel_usage is not None

            return fuel_model.evaluate_emissions(
                expression_evaluator=expression_evaluator,
                fuel_rate=fuel_usage.values,
            )

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


class GeneratorSet(BaseEquipment, Emitter, EnergyComponent):
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

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        return False

    def is_provider(self) -> bool:
        return True

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def evaluate_energy_usage(
        self, expression_evaluator: ExpressionEvaluator, context: ComponentEnergyContext
    ) -> dict[str, EcalcModelResult]:
        consumer_results: dict[str, EcalcModelResult] = {}
        fuel_consumer = Genset(
            id=self.id,
            name=self.name,
            temporal_generator_set_model=TemporalModel(
                {
                    period: GeneratorModelSampled(
                        fuel_values=model.fuel_values,
                        power_values=model.power_values,
                        energy_usage_adjustment_constant=model.energy_usage_adjustment_constant,
                        energy_usage_adjustment_factor=model.energy_usage_adjustment_factor,
                    )
                    for period, model in self.generator_set_model.items()
                }
            ),
        )

        consumer_results[self.id] = EcalcModelResult(
            component_result=fuel_consumer.evaluate(
                expression_evaluator=expression_evaluator,
                power_requirement=context.get_power_requirement(),
            ),
            models=[],
            sub_components=[],
        )

        return consumer_results

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
        expression_evaluator: ExpressionEvaluator,
    ) -> Optional[dict[str, EmissionResult]]:
        fuel_model = FuelModel(self.fuel)
        fuel_usage = energy_context.get_fuel_usage()

        assert fuel_usage is not None

        return fuel_model.evaluate_emissions(
            expression_evaluator=expression_evaluator,
            fuel_rate=fuel_usage.values,
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


class Installation(BaseComponent, EnergyComponent):
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

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        # Should maybe be True if power from shore?
        return False

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return True

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    @property
    def id(self) -> str:
        return generate_id(self.name)

    _validate_installation_temporal_model = field_validator("hydrocarbon_export")(validate_temporal_model)

    _convert_expression_installation = field_validator("regularity", "hydrocarbon_export", mode="before")(
        convert_expression
    )

    @field_validator("user_defined_category", mode="before")
    def check_user_defined_category(cls, user_defined_category, info: ValidationInfo):
        # Provide which value and context to make it easier for user to correct wrt mandatory changes.
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
            if self.fuel_consumers or self.venting_emitters:
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


class Asset(Component, EnergyComponent):
    @property
    def id(self):
        return generate_id(self.name)

    name: ComponentNameStr

    installations: list[Installation] = Field(default_factory=list)
    component_type: Literal[ComponentType.ASSET] = ComponentType.ASSET

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        # Should maybe be True if power from shore?
        return False

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return True

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

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


class FuelModel:
    """A function to evaluate fuel related attributes for different time period
    For each period, there is a data object with expressions for fuel related
    attributes which may be evaluated for some variables and a fuel_rate.
    """

    def __init__(self, fuel_time_function_dict: dict[Period, FuelType]):
        logger.debug("Creating fuel model")
        self.temporal_fuel_model = fuel_time_function_dict

    def evaluate_emissions(
        self, expression_evaluator: ExpressionEvaluator, fuel_rate: list[float]
    ) -> dict[str, EmissionResult]:
        """Evaluate fuel related expressions and results for a TimeSeriesCollection and a
        fuel_rate array.

        First the fuel parameters are calculated by evaluating the fuel expressions and
        the time_series object.

        Then the resulting emission volume is calculated based on the fuel rate:
        - emission_rate = emission_factor * fuel_rate

        This is done per time period and all fuel related results both in terms of
        fuel types and time periods, are merged into one common fuel collection results object.

        The length of the fuel_rate array must equal the length of the global list of periods.
        It is assumed that the fuel_rate array origins from calculations based on the same time_series
        object and thus will have the same length when used in this method.
        """
        logger.debug("Evaluating fuel usage and emissions")

        fuel_rate = np.asarray(fuel_rate)

        # Creating a pseudo-default dict with all the emitters as keys. This is to handle changes in a temporal model.
        emissions = {
            emission_name: EmissionResult.create_empty(name=emission_name, periods=Periods([]))
            for emission_name in {
                emission.name for _, model in self.temporal_fuel_model.items() for emission in model.emissions
            }
        }

        for temporal_period, model in self.temporal_fuel_model.items():
            if Period.intersects(temporal_period, expression_evaluator.get_period()):
                start_index, end_index = temporal_period.get_period_indices(expression_evaluator.get_periods())
                variables_map_this_period = expression_evaluator.get_subset(
                    start_index=start_index,
                    end_index=end_index,
                )
                fuel_rate_this_period = fuel_rate[start_index:end_index]
                for emission in model.emissions:
                    factor = variables_map_this_period.evaluate(expression=emission.factor)

                    emission_rate_kg_per_day = fuel_rate_this_period * factor
                    emission_rate_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate_kg_per_day)

                    result = EmissionResult(
                        name=emission.name,
                        periods=variables_map_this_period.get_periods(),
                        rate=TimeSeriesStreamDayRate(
                            periods=variables_map_this_period.get_periods(),
                            values=emission_rate_tons_per_day.tolist(),
                            unit=Unit.TONS_PER_DAY,
                        ),
                    )

                    emissions[emission.name].extend(result)

                for name in emissions:
                    if name not in [emission.name for emission in model.emissions]:
                        emissions[name].extend(
                            EmissionResult.create_empty(name=name, periods=variables_map_this_period.get_periods())
                        )

        return dict(sorted(emissions.items()))


@overload
def create_consumer(consumer: CompressorComponent, period: Period) -> Compressor: ...


@overload
def create_consumer(consumer: PumpComponent, period: Period) -> Pump: ...


def create_consumer(
    consumer: Union[CompressorComponent, PumpComponent],
    period: Period,
) -> Union[Compressor, Pump]:
    periods = consumer.energy_usage_model.keys()
    energy_usage_models = list(consumer.energy_usage_model.values())

    model_for_period = None
    for _period, energy_usage_model in zip(periods, energy_usage_models):
        if period in _period:
            model_for_period = energy_usage_model

    if model_for_period is None:
        raise ValueError(f"Could not find model for consumer {consumer.name} at timestep {period}")

    if consumer.component_type == ComponentType.COMPRESSOR:
        return Compressor(
            id=consumer.id,
            compressor_model=create_compressor_model(
                compressor_model_dto=model_for_period,
            ),
        )
    elif consumer.component_type == ComponentType.PUMP:
        return Pump(
            id=consumer.id,
            pump_model=create_pump_model(
                pump_model_dto=model_for_period,
            ),
        )
    else:
        raise TypeError(f"Unknown consumer. Received consumer with type '{consumer.component_type}'")
