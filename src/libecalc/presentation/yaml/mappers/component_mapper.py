from typing import Optional, Union

from pydantic import ValidationError

from libecalc.common.component_type import ComponentType
from libecalc.common.consumer_type import ConsumerType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.logger import logger
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.emitters.venting_emitter import (
    DirectVentingEmitter,
    EmissionRate,
    OilVentingEmitter,
    OilVolumeRate,
    VentingEmission,
    VentingVolume,
    VentingVolumeEmission,
)
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.base.component_dto import (
    Crossover,
    Priorities,
    SystemComponentConditions,
    SystemStreamConditions,
)
from libecalc.domain.infrastructure.energy_components.common import Consumer
from libecalc.domain.infrastructure.energy_components.compressor.component_dto import CompressorComponent
from libecalc.domain.infrastructure.energy_components.consumer_system.consumer_system_dto import ConsumerSystem
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_dto import GeneratorSet
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.domain.infrastructure.energy_components.pump.component_dto import PumpComponent
from libecalc.dto import ConsumerFunction, FuelType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException, ReferenceService
from libecalc.presentation.yaml.mappers.consumer_function_mapper import (
    ConsumerFunctionMapper,
)
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
)
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import YamlElectricityConsumer
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_fuel_consumer import YamlFuelConsumer
from libecalc.presentation.yaml.yaml_types.components.system.yaml_consumer_system import (
    YamlConsumerSystem,
    YamlPriorities,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import YamlGeneratorSet
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlDirectTypeEmitter,
    YamlOilTypeEmitter,
)

energy_usage_model_to_component_type_map = {
    ConsumerType.PUMP: ComponentType.PUMP,
    ConsumerType.PUMP_SYSTEM: ComponentType.PUMP_SYSTEM,
    ConsumerType.COMPRESSOR_SYSTEM: ComponentType.COMPRESSOR_SYSTEM,
    ConsumerType.COMPRESSOR: ComponentType.COMPRESSOR,
}

COMPRESSOR_TRAIN_ENERGY_MODEL_TYPES = [
    EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES,
    EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES,
    EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT,
    EnergyModelType.SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT,
    EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES,
]


def _get_component_type(energy_usage_models: dict[Period, ConsumerFunction]) -> ComponentType:
    energy_usage_model_types = {energy_usage_model.typ for energy_usage_model in energy_usage_models.values()}

    if len(energy_usage_model_types) == 1:
        energy_usage_model_type = energy_usage_model_types.pop()
        if energy_usage_model_type in energy_usage_model_to_component_type_map:
            return energy_usage_model_to_component_type_map[energy_usage_model_type]
        else:
            logger.debug(f"Uncaught energy usage model type '{energy_usage_model_types}'. Using generic type.")
            return ComponentType.GENERIC

    return ComponentType.GENERIC


def _resolve_fuel(
    consumer_fuel: Union[Optional[str], dict],
    default_fuel: Optional[str],
    references: ReferenceService,
    target_period: Period,
) -> Optional[dict[Period, FuelType]]:
    fuel = consumer_fuel or default_fuel  # Use parent fuel only if not specified on this consumer

    if fuel is None:
        return None

    time_adjusted_fuel = define_time_model_for_period(fuel, target_period=target_period)

    temporal_fuel_model = {}
    for period, fuel in time_adjusted_fuel.items():
        resolved_fuel = references.get_fuel_reference(fuel)

        temporal_fuel_model[period] = resolved_fuel

    return temporal_fuel_model


class ConsumerMapper:
    def __init__(self, references: ReferenceService, target_period: Period):
        self.__references = references
        self._target_period = target_period
        self.__energy_usage_model_mapper = ConsumerFunctionMapper(references=references, target_period=target_period)

    def from_yaml_consumers_to_domain(
        self,
        data: YamlConsumerSystem,
        regularity: dict[Period, Expression],
        consumes: ConsumptionType,
        fuel: Optional[dict[Period, FuelType]],
    ) -> Union[list[CompressorComponent], list[PumpComponent]]:
        return [
            consumer.to_dto(
                regularity=regularity,
                consumes=consumes,
                category=consumer.category,
                references=self.__references,
                target_period=self._target_period,
                fuel=fuel,
            )
            for consumer in data.consumers
        ]

    def from_yaml_consumer_system_to_domain(
        self,
        data: YamlConsumerSystem,
        regularity: dict[Period, Expression],
        consumes: ConsumptionType,
        expression_evaluator: ExpressionEvaluator,
        fuel: Optional[dict[Period, FuelType]],
    ) -> ConsumerSystem:
        consumers = self.from_yaml_consumers_to_domain(data=data, regularity=regularity, consumes=consumes, fuel=fuel)
        consumer_name_to_id_map = {consumer.name: consumer.id for consumer in consumers}

        try:
            return ConsumerSystem(
                name=data.name,
                user_defined_category=define_time_model_for_period(data.category, target_period=self._target_period),
                regularity=regularity,
                consumes=consumes,
                component_conditions=self.from_yaml_system_component_component_conditions_to_domain(
                    data=data, consumer_name_to_id_map=consumer_name_to_id_map
                ),
                priorities=self.from_yaml_priorities_to_domain(yaml_priorities=data.stream_conditions_priorities),
                consumers=consumers,
                expression_evaluator=expression_evaluator,
                target_period=self._target_period,
                fuel=fuel,
                component_type=data.component_type,
            )
        except ValidationError as e:
            raise DtoValidationError(data=data.model_dump(), validation_error=e) from e

    @staticmethod
    def from_yaml_system_component_component_conditions_to_domain(
        data: YamlConsumerSystem, consumer_name_to_id_map: dict[str, str]
    ) -> SystemComponentConditions:
        if data.component_conditions is not None:
            return SystemComponentConditions(
                crossover=[
                    Crossover(
                        from_component_id=consumer_name_to_id_map[crossover_stream.from_],
                        to_component_id=consumer_name_to_id_map[crossover_stream.to],
                        stream_name=crossover_stream.name,
                    )
                    for crossover_stream in data.component_conditions.crossover
                ]
                if data.component_conditions.crossover is not None
                else [],
            )
        else:
            return SystemComponentConditions(crossover=[])

    @staticmethod
    def from_yaml_priorities_to_domain(yaml_priorities: YamlPriorities) -> Priorities[SystemStreamConditions]:
        priorities: Priorities[SystemStreamConditions] = {}
        for priority_id, consumer_map in yaml_priorities.items():
            priorities[priority_id] = {}
            for consumer_id, stream_conditions in consumer_map.items():
                priorities[priority_id][consumer_id] = {
                    stream_name: SystemStreamConditions(
                        rate=stream_conditions.rate,
                        pressure=stream_conditions.pressure,
                        fluid_density=stream_conditions.fluid_density,
                    )
                    for stream_name, stream_conditions in stream_conditions.items()
                }
        return priorities

    def from_yaml_to_domain(
        self,
        data: Union[YamlFuelConsumer, YamlElectricityConsumer, YamlConsumerSystem],
        regularity: dict[Period, Expression],
        consumes: ConsumptionType,
        expression_evaluator: ExpressionEvaluator,
        default_fuel: Optional[str] = None,
    ) -> Consumer:
        component_type = data.component_type
        if component_type not in [ComponentType.CONSUMER_SYSTEM_V2.value, "FUEL_CONSUMER", "ELECTRICITY_CONSUMER"]:
            # We have type here for v2, check that type is valid
            raise DataValidationError(
                data=data.model_dump(),
                message=f"Invalid component type '{component_type}' for component with name '{data.name}'",
            )

        fuel = None
        if consumes == ConsumptionType.FUEL:
            consumer_fuel = data.fuel if hasattr(data, "fuel") else None  # YamlConsumerSystem does not have fuel
            try:
                fuel = _resolve_fuel(consumer_fuel, default_fuel, self.__references, target_period=self._target_period)
            except InvalidReferenceException as e:
                raise DataValidationError(
                    data=data.model_dump(),
                    message=str(e),
                    error_key="fuel",
                ) from e

        if isinstance(data, YamlConsumerSystem):
            try:
                return self.from_yaml_consumer_system_to_domain(
                    data=data,
                    regularity=regularity,
                    consumes=consumes,
                    expression_evaluator=expression_evaluator,
                    fuel=fuel,
                )
            except ValidationError as e:
                raise DtoValidationError(data=data.model_dump(), validation_error=e) from e

        try:
            energy_usage_model = self.__energy_usage_model_mapper.from_yaml_to_dto(data.energy_usage_model)
        except ValidationError as e:
            raise DtoValidationError(data=data.model_dump(), validation_error=e) from e

        if consumes == ConsumptionType.FUEL:
            try:
                fuel_consumer_name = data.name
                return FuelConsumer(
                    name=fuel_consumer_name,
                    user_defined_category=define_time_model_for_period(
                        data.category, target_period=self._target_period
                    ),
                    regularity=regularity,
                    fuel=fuel,
                    energy_usage_model=energy_usage_model,
                    component_type=_get_component_type(energy_usage_model),
                    consumes=consumes,
                    expression_evaluator=expression_evaluator,
                )
            except ValidationError as e:
                raise DtoValidationError(data=data.model_dump(), validation_error=e) from e
        else:
            try:
                electricity_consumer_name = data.name
                return ElectricityConsumer(
                    name=electricity_consumer_name,
                    regularity=regularity,
                    user_defined_category=define_time_model_for_period(
                        data.category, target_period=self._target_period
                    ),
                    energy_usage_model=energy_usage_model,
                    component_type=_get_component_type(energy_usage_model),
                    consumes=consumes,
                    expression_evaluator=expression_evaluator,
                )
            except ValidationError as e:
                raise DtoValidationError(data=data.model_dump(), validation_error=e) from e


class GeneratorSetMapper:
    def __init__(self, references: ReferenceService, target_period: Period):
        self.__references = references
        self._target_period = target_period
        self.__consumer_mapper = ConsumerMapper(references=references, target_period=target_period)

    def from_yaml_to_domain(
        self,
        data: YamlGeneratorSet,
        regularity: dict[Period, Expression],
        expression_evaluator: ExpressionEvaluator,
        default_fuel: Optional[str] = None,
    ) -> GeneratorSet:
        try:
            fuel = _resolve_fuel(data.fuel, default_fuel, self.__references, target_period=self._target_period)
        except ValueError as e:
            raise DataValidationError(
                data=data.model_dump(),
                message=f"Fuel '{data.fuel}' does not exist",  # TODO: What if default fuel does not exist?
                error_key="fuel",
            ) from e
        generator_set_model_data = define_time_model_for_period(
            data.electricity2fuel, target_period=self._target_period
        )
        generator_set_model = {
            start_time: self.__references.get_generator_set_model(model_reference)
            for start_time, model_reference in generator_set_model_data.items()
        }

        # When consumers was created directly in the return dto.GeneratorSet - function,
        # the error message indicated some problems in the creation of consumers, but was due to a validation error for
        # the generator sets electricity to fuel input. Thus, create/parse things one by one to ensure reliable errors
        consumers = [
            self.__consumer_mapper.from_yaml_to_domain(
                consumer,
                regularity=regularity,
                consumes=ConsumptionType.ELECTRICITY,
                expression_evaluator=expression_evaluator,
            )
            for consumer in data.consumers or []
        ]
        user_defined_category = define_time_model_for_period(data.category, target_period=self._target_period)

        cable_loss = convert_expression(data.cable_loss)
        max_usage_from_shore = convert_expression(data.max_usage_from_shore)

        try:
            generator_set_name = data.name
            return GeneratorSet(
                name=generator_set_name,
                fuel=fuel,
                regularity=regularity,
                generator_set_model=generator_set_model,
                consumers=consumers,
                user_defined_category=user_defined_category,
                cable_loss=cable_loss,
                max_usage_from_shore=max_usage_from_shore,
                component_type=ComponentType.GENERATOR_SET,
                expression_evaluator=expression_evaluator,
            )
        except ValidationError as e:
            raise DtoValidationError(data=data.model_dump(), validation_error=e) from e


class InstallationMapper:
    def __init__(self, references: ReferenceService, target_period: Period):
        self.__references = references
        self._target_period = target_period
        self.__generator_set_mapper = GeneratorSetMapper(references=references, target_period=target_period)
        self.__consumer_mapper = ConsumerMapper(references=references, target_period=target_period)

    def from_yaml_venting_emitter_to_domain(
        self,
        data: Union[YamlDirectTypeEmitter, YamlOilTypeEmitter],
        expression_evaluator: ExpressionEvaluator,
        regularity: dict[Period, Expression],
    ) -> Union[DirectVentingEmitter, OilVentingEmitter]:
        if isinstance(data, YamlDirectTypeEmitter):
            emissions = [
                VentingEmission(
                    name=emission.name,
                    emission_rate=EmissionRate(
                        value=emission.rate.value,
                        unit=emission.rate.unit.to_unit(),
                        rate_type=emission.rate.type,
                    ),
                )
                for emission in data.emissions
            ]

            return DirectVentingEmitter(
                name=data.name,
                expression_evaluator=expression_evaluator,
                component_type=data.component_type,
                user_defined_category=data.category,
                emitter_type=data.type,
                emissions=emissions,
                regularity=regularity,
            )
        elif isinstance(data, YamlOilTypeEmitter):
            return OilVentingEmitter(
                name=data.name,
                expression_evaluator=expression_evaluator,
                component_type=data.component_type,
                user_defined_category=data.category,
                emitter_type=data.type,
                volume=VentingVolume(
                    oil_volume_rate=OilVolumeRate(
                        value=data.volume.rate.value,
                        unit=data.volume.rate.unit.to_unit(),
                        rate_type=data.volume.rate.type,
                    ),
                    emissions=[
                        VentingVolumeEmission(name=emission.name, emission_factor=emission.emission_factor)
                        for emission in data.volume.emissions
                    ],
                ),
                regularity=regularity,
            )
        else:
            raise TypeError("Unsupported YamlVentingEmitter type")

    def from_yaml_to_domain(self, data: YamlInstallation, expression_evaluator: ExpressionEvaluator) -> Installation:
        fuel_data = data.fuel
        regularity = define_time_model_for_period(
            convert_expression(data.regularity or 1), target_period=self._target_period
        )

        installation_name = data.name

        generator_sets = [
            self.__generator_set_mapper.from_yaml_to_domain(
                generator_set,
                regularity=regularity,
                default_fuel=fuel_data,
                expression_evaluator=expression_evaluator,
            )
            for generator_set in data.generator_sets or []
        ]
        fuel_consumers = [
            self.__consumer_mapper.from_yaml_to_domain(
                fuel_consumer,
                regularity=regularity,
                consumes=ConsumptionType.FUEL,
                default_fuel=fuel_data,
                expression_evaluator=expression_evaluator,
            )
            for fuel_consumer in data.fuel_consumers or []
        ]

        hydrocarbon_export = define_time_model_for_period(
            data.hydrocarbon_export or Expression.setup_from_expression(0),
            target_period=self._target_period,
        )

        venting_emitters = [
            self.from_yaml_venting_emitter_to_domain(
                venting_emitter,
                expression_evaluator=expression_evaluator,
                regularity=regularity,
            )
            for venting_emitter in data.venting_emitters or []
        ]
        # venting_emitters = [
        #     venting_emitter.to_domain(expression_evaluator, regularity)
        #     for venting_emitter in data.venting_emitters or []
        # ]

        try:
            return Installation(
                name=installation_name,
                regularity=regularity,
                hydrocarbon_export=hydrocarbon_export,
                fuel_consumers=[*generator_sets, *fuel_consumers],
                venting_emitters=venting_emitters,
                user_defined_category=data.category,
                expression_evaluator=expression_evaluator,
            )
        except ValidationError as e:
            raise DtoValidationError(data=data.model_dump(), validation_error=e) from e


class EcalcModelMapper:
    def __init__(
        self,
        references: ReferenceService,
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
    ):
        self.__references = references
        self.__installation_mapper = InstallationMapper(references=references, target_period=target_period)
        self.__expression_evaluator = expression_evaluator

    def from_yaml_to_domain(self, configuration: YamlValidator) -> Asset:
        try:
            ecalc_model = Asset(
                name=configuration.name,
                installations=[
                    self.__installation_mapper.from_yaml_to_domain(
                        installation, expression_evaluator=self.__expression_evaluator
                    )
                    for installation in configuration.installations
                ],
            )
            return ecalc_model
        except ValidationError as e:
            raise DtoValidationError(data=None, validation_error=e) from e
