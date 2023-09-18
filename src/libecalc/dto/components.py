from abc import ABC
from datetime import datetime
from typing import Dict, List, Literal, Optional, TypeVar, Union

import networkx as nx
from libecalc import dto
from libecalc.common.string_utils import generate_id, get_duplicates
from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesRate
from libecalc.dto.base import (
    Component,
    ComponentType,
    ConsumerUserDefinedCategoryType,
    EcalcBaseModel,
    InstallationUserDefinedCategoryType,
)
from libecalc.dto.core_specs.system.operational_settings import (
    EvaluatedCompressorSystemOperationalSettings,
    EvaluatedPumpSystemOperationalSettings,
)
from libecalc.dto.graph import Graph
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
    EmissionNameStr,
    convert_expression,
    validate_temporal_model,
)
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression
from pydantic import Field, root_validator
from pydantic.class_validators import validator
from typing_extensions import Annotated


def check_model_energy_usage_type(model_data: Dict[datetime, ConsumerFunction], energy_type: EnergyUsageType):
    for model in model_data.values():
        if model.energy_usage_type != energy_type:
            raise ValueError(f"Model does not consume {energy_type}")
    return model_data


class BaseComponent(Component, ABC):
    name: ComponentNameStr

    regularity: Dict[datetime, Expression]

    _validate_base_temporal_model = validator("regularity", allow_reuse=True)(validate_temporal_model)


class BaseEquipment(BaseComponent, ABC):
    user_defined_category: Dict[datetime, ConsumerUserDefinedCategoryType]

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @validator("user_defined_category", pre=True, always=True)
    def check_user_defined_category(cls, user_defined_category, values):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if isinstance(user_defined_category, dict) and len(user_defined_category.values()) > 0:
            for user_category in user_defined_category.values():
                if user_category not in list(ConsumerUserDefinedCategoryType):
                    name = ""
                    if values.get("name") is not None:
                        name = f"with the name {values.get('name')}"

                    raise ValueError(
                        f"CATEGORY: {user_category} is not allowed for {cls.__name__} {name}. Valid categories are: {[(consumer_user_defined_category.value) for consumer_user_defined_category in ConsumerUserDefinedCategoryType]}"
                    )

        return user_defined_category


class BaseConsumer(BaseEquipment, ABC):
    """Base class for all consumers."""

    consumes: ConsumptionType
    fuel: Optional[Dict[datetime, FuelType]]

    @validator("fuel")
    def validate_fuel_exist(cls, fuel, values):
        """
        Make sure fuel is set if consumption type is FUEL.
        """
        if values.get("consumes") == ConsumptionType.FUEL and (fuel is None or len(fuel) < 1):
            msg = f"Missing fuel for fuel consumer '{values.get('name')}'"
            raise ValueError(msg)
        return fuel


class ElectricityConsumer(BaseConsumer):
    consumes: Literal[ConsumptionType.ELECTRICITY] = ConsumptionType.ELECTRICITY
    energy_usage_model: Dict[
        datetime,
        ElectricEnergyUsageModel,
    ]

    _validate_el_consumer_temporal_model = validator("energy_usage_model", allow_reuse=True)(validate_temporal_model)

    _check_model_energy_usage = validator("energy_usage_model", allow_reuse=True)(
        lambda data: check_model_energy_usage_type(data, EnergyUsageType.POWER)
    )


class FuelConsumer(BaseConsumer):
    consumes: Literal[ConsumptionType.FUEL] = ConsumptionType.FUEL
    fuel: Dict[datetime, FuelType]
    energy_usage_model: Dict[datetime, FuelEnergyUsageModel]

    _validate_fuel_consumer_temporal_models = validator("energy_usage_model", "fuel", allow_reuse=True)(
        validate_temporal_model
    )

    _check_model_energy_usage = validator("energy_usage_model", allow_reuse=True)(
        lambda data: check_model_energy_usage_type(data, EnergyUsageType.FUEL)
    )


Consumer = Annotated[Union[FuelConsumer, ElectricityConsumer], Field(discriminator="consumes")]


class EmitterModel(EcalcBaseModel):
    name: ComponentNameStr = ""  # This is not mandatory yet.
    user_defined_category: str = ""  # This is not mandatory yet.
    emission_rate: Expression
    emission_quota: Expression

    regularity: Dict[datetime, Expression]

    _validate_emitter_model_temporal_model = validator("regularity", allow_reuse=True)(validate_temporal_model)

    _default_emission_rate = validator("emission_rate", allow_reuse=True, pre=True)(convert_expression)
    _default_emission_quota = validator("emission_quota", allow_reuse=True, pre=True)(convert_expression)


class DirectEmitter(BaseEquipment):
    component_type = ComponentType.DIRECT_EMITTER
    emission_name: EmissionNameStr
    emitter_model: Dict[datetime, EmitterModel]

    _validate_emitter_temporal_model = validator("emitter_model", allow_reuse=True)(validate_temporal_model)


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


ConsumerComponent = TypeVar("ConsumerComponent", bound=Union[CompressorComponent, PumpComponent])


class CompressorSystemOperationalSetting(EcalcBaseModel):
    rates: List[Expression]
    inlet_pressures: List[Expression]
    outlet_pressures: List[Expression]
    crossover: List[int]


class PumpSystemOperationalSetting(EcalcBaseModel):
    fluid_density: List[Expression]
    rates: List[Expression]
    inlet_pressures: List[Expression]
    outlet_pressures: List[Expression]
    crossover: List[int]


class CompressorSystem(BaseConsumer):
    component_type: Literal[ComponentType.COMPRESSOR_SYSTEM_V2] = ComponentType.COMPRESSOR_SYSTEM_V2
    operational_settings: Dict[datetime, List[CompressorSystemOperationalSetting]]
    compressors: List[CompressorComponent]

    def get_graph(self) -> Graph:
        component_dtos = {}
        graph = nx.DiGraph()
        graph.add_node(self.id)
        component_dtos[self.id] = self
        for compressor in self.compressors:
            component_dtos[compressor.id] = compressor
            graph.add_edge(self.id, compressor.id)
        return Graph(
            graph=graph,
            components=component_dtos,
        )

    def evaluate_operational_settings(
        self,
        variables_map: VariablesMap,
    ) -> TemporalModel[List[EvaluatedCompressorSystemOperationalSettings]]:
        """Parameters
        ----------
        variables_map
        operational_settings
        Returns
        -------
        """
        evaluated_regularity = TemporalExpression.evaluate(
            temporal_expression=TemporalModel(self.regularity), variables_map=variables_map
        )
        evaluated_temporal_operational_settings: Dict[datetime, List[EvaluatedCompressorSystemOperationalSettings]] = {}
        for period, operational_settings in TemporalModel(self.operational_settings).items():
            period_start, period_end = period.get_timestep_indices(variables_map.time_vector)
            regularity_for_period = evaluated_regularity[period_start:period_end]
            evaluated_operational_settings: List[EvaluatedCompressorSystemOperationalSettings] = []
            for operational_setting in operational_settings:
                rates: List[TimeSeriesRate] = [
                    TimeSeriesRate(
                        values=list(rate.evaluate(variables_map.variables, fill_length=len(variables_map.time_vector))),
                        timesteps=variables_map.time_vector,
                        regularity=regularity_for_period,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    )
                    for rate in operational_setting.rates
                ]

                inlet_pressure = [
                    TimeSeriesFloat(
                        values=list(
                            pressure.evaluate(variables_map.variables, fill_length=len(variables_map.time_vector))
                        ),
                        timesteps=variables_map.time_vector,
                        unit=Unit.BARA,
                    )
                    for pressure in operational_setting.inlet_pressures
                ]
                outlet_pressure = [
                    TimeSeriesFloat(
                        values=list(
                            pressure.evaluate(variables_map.variables, fill_length=len(variables_map.time_vector))
                        ),
                        timesteps=variables_map.time_vector,
                        unit=Unit.BARA,
                    )
                    for pressure in operational_setting.outlet_pressures
                ]

                evaluated_operational_settings.append(
                    EvaluatedCompressorSystemOperationalSettings(
                        rates=rates,
                        inlet_pressures=inlet_pressure,
                        outlet_pressures=outlet_pressure,
                        crossover=operational_setting.crossover,
                    )
                )
            evaluated_temporal_operational_settings[period.start] = evaluated_operational_settings

        return TemporalModel(evaluated_temporal_operational_settings)


class PumpSystem(BaseConsumer):
    component_type: Literal[ComponentType.PUMP_SYSTEM_V2] = ComponentType.PUMP_SYSTEM_V2
    operational_settings: Dict[datetime, List[PumpSystemOperationalSetting]]
    pumps: List[PumpComponent]

    def evaluate_operational_settings(
        self,
        variables_map: VariablesMap,
    ) -> TemporalModel[List[EvaluatedPumpSystemOperationalSettings]]:
        evaluated_regularity = TemporalExpression.evaluate(
            temporal_expression=TemporalModel(self.regularity), variables_map=variables_map
        )

        evaluated_temporal_operational_settings: Dict[datetime, List[EvaluatedPumpSystemOperationalSettings]] = {}
        for period, operational_settings in TemporalModel(self.operational_settings).items():
            period_start, period_end = period.get_timestep_indices(variables_map.time_vector)
            regularity_for_period = evaluated_regularity[period_start:period_end]
            evaluated_operational_settings: List[EvaluatedPumpSystemOperationalSettings] = []
            for operational_setting in operational_settings:
                rates: List[TimeSeriesRate] = [
                    TimeSeriesRate(
                        values=list(rate.evaluate(variables_map.variables, fill_length=len(variables_map.time_vector))),
                        timesteps=variables_map.time_vector,
                        regularity=regularity_for_period,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    )
                    for rate in operational_setting.rates
                ]

                inlet_pressure = [
                    TimeSeriesFloat(
                        values=list(rate.evaluate(variables_map.variables, fill_length=len(variables_map.time_vector))),
                        timesteps=variables_map.time_vector,
                        unit=Unit.BARA,
                    )
                    for rate in operational_setting.inlet_pressures
                ]
                outlet_pressure = [
                    TimeSeriesFloat(
                        values=list(rate.evaluate(variables_map.variables, fill_length=len(variables_map.time_vector))),
                        timesteps=variables_map.time_vector,
                        unit=Unit.BARA,
                    )
                    for rate in operational_setting.outlet_pressures
                ]

                fluid_density = [
                    TimeSeriesFloat(
                        values=list(rate.evaluate(variables_map.variables, fill_length=len(variables_map.time_vector))),
                        timesteps=variables_map.time_vector,
                        unit=Unit.KG_SM3,
                    )
                    for rate in operational_setting.fluid_density
                ]

                evaluated_operational_settings.append(
                    EvaluatedPumpSystemOperationalSettings(
                        rates=rates,
                        inlet_pressures=inlet_pressure,
                        outlet_pressures=outlet_pressure,
                        fluid_density=fluid_density,
                        crossover=operational_setting.crossover,
                    )
                )
            evaluated_temporal_operational_settings[period.start] = evaluated_operational_settings

        return TemporalModel(evaluated_temporal_operational_settings)


class GeneratorSet(BaseEquipment):
    component_type: Literal[ComponentType.GENERATOR_SET] = ComponentType.GENERATOR_SET
    fuel: Dict[datetime, FuelType]
    generator_set_model: Dict[datetime, GeneratorSetSampled]
    consumers: List[Union[ElectricityConsumer, CompressorSystem, PumpSystem]] = Field(default_factory=list)
    _validate_genset_temporal_models = validator("generator_set_model", "fuel", allow_reuse=True)(
        validate_temporal_model
    )

    @validator("user_defined_category", pre=True, always=True)
    def check_mandatory_category_for_generator_set(cls, user_defined_category):
        """This could be handled automatically with Pydantic, but I want to inform the users in a better way, in
        particular since we introduced a breaking change for this to be mandatory for GeneratorSets in v7.2.
        """
        if user_defined_category is None or user_defined_category == "":
            raise ValueError(f"CATEGORY is mandatory and must be set for {cls.__name__}")

        return user_defined_category

    def get_graph(self) -> Graph:
        component_dtos = {}
        graph = nx.DiGraph()
        graph.add_node(self.id)
        component_dtos[self.id] = self

        for electricity_consumer in self.consumers:
            component_dtos[electricity_consumer.id] = electricity_consumer
            graph.add_node(electricity_consumer.id)
            graph.add_edge(self.id, electricity_consumer.id)

        return Graph(
            graph=graph,
            components=component_dtos,
        )


class Installation(BaseComponent):
    component_type = ComponentType.INSTALLATION
    user_defined_category: Optional[InstallationUserDefinedCategoryType] = None
    hydrocarbon_export: Dict[datetime, Expression]
    fuel_consumers: List[Union[GeneratorSet, FuelConsumer, CompressorSystem, PumpSystem]] = Field(default_factory=list)
    direct_emitters: List[DirectEmitter] = Field(default_factory=list)

    @property
    def id(self) -> str:
        return generate_id(self.name)

    _validate_installation_temporal_model = validator("hydrocarbon_export", allow_reuse=True)(validate_temporal_model)

    _convert_expression_installation = validator("regularity", "hydrocarbon_export", allow_reuse=True, pre=True)(
        convert_expression
    )

    @validator("user_defined_category", pre=True, always=True)
    def check_user_defined_category(cls, user_defined_category, values):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if user_defined_category is not None:
            if user_defined_category not in list(InstallationUserDefinedCategoryType):
                name = ""
                if values.get("name") is not None:
                    name = f"with the name {values.get('name')}"

                raise ValueError(
                    f"CATEGORY: {user_defined_category} is not allowed for {cls.__name__} {name}. Valid categories are: {[str(installation_user_defined_category.value) for installation_user_defined_category in InstallationUserDefinedCategoryType]}"
                )

        return user_defined_category

    def get_graph(self) -> Graph:
        component_dtos = {}
        graph = nx.DiGraph()
        graph.add_node(self.id)
        component_dtos[self.id] = self
        for fuel_consumer in self.fuel_consumers:
            component_dtos[fuel_consumer.id] = fuel_consumer

            if hasattr(fuel_consumer, "get_graph"):
                generator_set_graph = fuel_consumer.get_graph()
                component_dtos.update(generator_set_graph.components)
                graph = nx.compose(graph, generator_set_graph.graph)
                graph.add_edge(self.id, fuel_consumer.id)
            else:
                graph.add_node(fuel_consumer.id)
                graph.add_edge(self.id, fuel_consumer.id)

        for direct_emitter in self.direct_emitters:
            component_dtos[direct_emitter.id] = direct_emitter
            graph.add_node(direct_emitter.id)
            graph.add_edge(self.id, direct_emitter.id)
        return Graph(
            graph=graph,
            components=component_dtos,
        )


class Asset(Component):
    @property
    def id(self):
        return generate_id(self.component_type, self.name)

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

        for emitter in installation.direct_emitters:
            component_ids.append(emitter.id)
        return component_ids

    def get_installation(self, installation_id: str) -> Installation:
        return next(installation for installation in self.installations if installation.id == installation_id)

    @root_validator(skip_on_failure=True)
    def validate_unique_names(cls, values):
        """Ensure unique component names within installation."""
        names = [values["name"]]
        fuel_types = [dto.FuelType]
        fuel_names = [str]
        for installation in values["installations"]:
            names.append(installation.name)
            fuel_consumers = installation.fuel_consumers
            direct_emitters = installation.direct_emitters

            names.extend([direct_emitter.name for direct_emitter in direct_emitters])
            for fuel_consumer in fuel_consumers:
                names.append(fuel_consumer.name)
                if isinstance(fuel_consumer, GeneratorSet):
                    for electricity_consumer in fuel_consumer.consumers:
                        names.append(electricity_consumer.name)
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
                "Component names must be unique. Components include asset/ecalc-model, installations,"
                " generator sets, electricity consumers, fuel consumers and direct emitters."
                f" Duplicated names are: {', '.join(duplicated_names)}"
            )

        if len(duplicated_fuel_names) > 0:
            raise ValueError(
                "Fuel type names must be unique across installations."
                f" Duplicated names are: {', '.join(duplicated_fuel_names)}"
            )
        return values

    def get_graph(self) -> Graph:
        component_dtos = {}
        graph = nx.DiGraph()
        graph.add_node(self.id)
        component_dtos[self.id] = self
        for installation in self.installations:
            component_dtos[installation.id] = installation
            installation_graph = installation.get_graph()
            component_dtos.update(installation_graph.components)
            graph = nx.compose(graph, installation_graph.graph)
            graph.add_edge(self.id, installation.id)
        return Graph(
            graph=graph,
            components=component_dtos,
        )


ComponentDTO = Union[
    Asset,
    Installation,
    GeneratorSet,
    FuelConsumer,
    ElectricityConsumer,
    PumpSystem,
    CompressorSystem,
    CompressorComponent,
    PumpComponent,
]
