from typing import assert_never

from pydantic import ValidationError

from libecalc.common.component_type import ComponentType
from libecalc.common.consumer_type import ConsumerType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.temporal_model import InvalidTemporalModel, TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.component_validation_error import (
    ComponentValidationException,
    ModelValidationError,
)
from libecalc.domain.hydrocarbon_export import HydrocarbonExport, InvalidHydrocarbonExport
from libecalc.domain.infrastructure.emitters.fuel_consumer_emitter import FuelConsumerEmitter
from libecalc.domain.infrastructure.emitters.venting_emitter import (
    DirectVentingEmitter,
    EmissionRate,
    OilStorageContainer,
    OilVentingEmitter,
    OilVolumeRate,
    VentingEmission,
    VentingEmitterComponent,
    VentingVolumeEmission,
)
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.common import Consumer
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel import Fuel
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import InvalidRegularity, Regularity
from libecalc.domain.storage_container import StorageContainer
from libecalc.dto.utils.validators import convert_expression
from libecalc.presentation.yaml.domain.emission_model import EmissionContainer, EmissionRegistry
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException, ReferenceService
from libecalc.presentation.yaml.domain.temporal_emissions import TemporalEmissionFactors
from libecalc.presentation.yaml.mappers.consumer_function_mapper import (
    ConsumerFunctionMapper,
    InvalidEnergyUsageModelException,
)
from libecalc.presentation.yaml.mappers.yaml_mapping_context import MappingContext
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.validation_errors import DtoValidationError
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model import (
    YamlElectricityEnergyUsageModel,
    YamlEnergyUsageModelCompressor,
    YamlEnergyUsageModelCompressorSystem,
    YamlEnergyUsageModelCompressorTrainMultipleStreams,
    YamlEnergyUsageModelDirectElectricity,
    YamlEnergyUsageModelDirectFuel,
    YamlEnergyUsageModelPump,
    YamlEnergyUsageModelPumpSystem,
    YamlEnergyUsageModelTabulated,
    YamlFuelEnergyUsageModel,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import YamlElectricityConsumer
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_fuel_consumer import YamlFuelConsumer
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import YamlGeneratorSet
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlDirectTypeEmitter,
    YamlOilTypeEmitter,
)
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel

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


def _get_model_type(model: YamlFuelEnergyUsageModel | YamlElectricityEnergyUsageModel):
    if isinstance(model, YamlEnergyUsageModelDirectElectricity | YamlEnergyUsageModelDirectFuel):
        return ComponentType.GENERIC
    elif isinstance(model, YamlEnergyUsageModelCompressor):
        return ComponentType.COMPRESSOR
    elif isinstance(model, YamlEnergyUsageModelPump):
        return ComponentType.PUMP
    elif isinstance(model, YamlEnergyUsageModelCompressorSystem):
        return ComponentType.COMPRESSOR_SYSTEM
    elif isinstance(model, YamlEnergyUsageModelPumpSystem):
        return ComponentType.PUMP_SYSTEM
    elif isinstance(model, YamlEnergyUsageModelTabulated):
        return ComponentType.GENERIC
    elif isinstance(model, YamlEnergyUsageModelCompressorTrainMultipleStreams):
        return ComponentType.COMPRESSOR
    else:
        return assert_never(model)


def _get_component_type(
    energy_usage_models: YamlTemporalModel[YamlFuelEnergyUsageModel]
    | YamlTemporalModel[YamlElectricityEnergyUsageModel],
) -> ComponentType:
    if not isinstance(energy_usage_models, dict):
        models = [energy_usage_models]
    else:
        models = energy_usage_models.values()
    energy_usage_model_types = set()
    for model in models:
        energy_usage_model_types.add(_get_model_type(model))

    if len(energy_usage_model_types) == 1:
        return energy_usage_model_types.pop()

    return ComponentType.GENERIC


class MissingFuelReference(Exception):
    def __init__(self):
        super().__init__("Missing fuel reference")


def _resolve_fuel(
    consumer_fuel: str | None | dict,
    default_fuel: str | None,
    references: ReferenceService,
    target_period: Period,
) -> TemporalModel[YamlFuelType]:
    fuel = consumer_fuel or default_fuel  # Use parent fuel only if not specified on this consumer

    if fuel is None:
        raise MissingFuelReference()

    time_adjusted_fuel = define_time_model_for_period(fuel, target_period=target_period)

    temporal_fuel_model = {}
    for period, fuel_reference in time_adjusted_fuel.items():
        resolved_fuel = references.get_fuel_reference(fuel_reference)  # type: ignore[arg-type]

        temporal_fuel_model[period] = resolved_fuel

    return TemporalModel(temporal_fuel_model)


class ConsumerMapper:
    def __init__(self, references: ReferenceService, target_period: Period, emission_registry: EmissionRegistry):
        self.__references = references
        self._target_period = target_period
        self._emission_registry = emission_registry
        self.__energy_usage_model_mapper = ConsumerFunctionMapper(references=references, target_period=target_period)

    def from_yaml_to_domain(
        self,
        data: YamlFuelConsumer | YamlElectricityConsumer,
        regularity: Regularity,
        consumes: ConsumptionType,
        expression_evaluator: ExpressionEvaluator,
        configuration: YamlValidator,
        yaml_path: YamlPath,
        mapping_context: MappingContext,
        parent_id: PathID,
        default_fuel: str | None = None,
    ) -> Consumer:
        def create_error_from_key(
            message: str,
            key: str,
        ) -> ModelValidationError:
            key_path: YamlPath = yaml_path.append(key)
            file_context = configuration.get_file_context(key_path.keys) or configuration.get_file_context(
                yaml_path.keys
            )
            return ModelValidationError(
                message=message,
                location=mapping_context.get_location_from_yaml_path(key_path),
                name=data.name,
                file_context=file_context,
            )

        def create_error_from_yaml_path(
            message: str,
            specific_path: YamlPath,
        ):
            file_context = configuration.get_file_context(specific_path.keys) or configuration.get_file_context(
                yaml_path.keys
            )
            return ModelValidationError(
                message=message,
                location=mapping_context.get_location_from_yaml_path(specific_path),
                name=data.name,
                file_context=file_context,
            )

        try:
            energy_usage_model = self.__energy_usage_model_mapper.from_yaml_to_dto(
                data.energy_usage_model,
                consumes=consumes,
            )
        except InvalidEnergyUsageModelException as e:
            energy_usage_model_yaml_path = yaml_path.append("ENERGY_USAGE_MODEL")
            specific_model_path = energy_usage_model_yaml_path.append(e.period.start)
            raise ComponentValidationException(
                errors=[
                    create_error_from_yaml_path(
                        message=e.message,
                        specific_path=specific_model_path,
                    )
                ]
            ) from e
        except InvalidTemporalModel as e:
            raise ComponentValidationException(
                errors=[create_error_from_key(message=str(e), key="ENERGY_USAGE_MODEL")]
            ) from e

        consumer_id = PathID(data.name)
        if consumes == ConsumptionType.FUEL:
            fuel = _resolve_fuel(data.fuel, default_fuel, self.__references, target_period=self._target_period)
            try:
                fuel_consumer_emitter = FuelConsumerEmitter(
                    entity_id=consumer_id,
                    emissions=TemporalEmissionFactors(expression_evaluator=expression_evaluator, temporal_fuel=fuel),
                )
                self._emission_registry.add_emitter(fuel_consumer_emitter, parent_container_id=parent_id)
            except InvalidReferenceException as e:
                raise ComponentValidationException(errors=[create_error_from_key(str(e), key="fuel")]) from e
            except MissingFuelReference as e:
                raise ComponentValidationException(errors=[create_error_from_key(str(e), key="fuel")]) from e
            except InvalidTemporalModel as e:
                raise ComponentValidationException(errors=[create_error_from_key(str(e), key="fuel")]) from e

            return FuelConsumer(
                path_id=PathID(data.name),
                user_defined_category=define_time_model_for_period(  # type: ignore[arg-type]
                    data.category, target_period=self._target_period
                ),
                regularity=regularity,
                temporal_fuel=TemporalModel(
                    {period: Fuel(name=fuel.name, category=fuel.category) for period, fuel in fuel.items()}
                ),
                energy_usage_model=energy_usage_model,
                component_type=_get_component_type(data.energy_usage_model),
                expression_evaluator=expression_evaluator,
            )
        else:
            return ElectricityConsumer(
                path_id=PathID(data.name),
                regularity=regularity,
                user_defined_category=define_time_model_for_period(  # type: ignore[arg-type]
                    data.category, target_period=self._target_period
                ),
                energy_usage_model=energy_usage_model,
                component_type=_get_component_type(data.energy_usage_model),
                consumes=consumes,
                expression_evaluator=expression_evaluator,
            )


class GeneratorSetMapper:
    def __init__(self, references: ReferenceService, target_period: Period, emission_registry: EmissionRegistry):
        self.__references = references
        self._target_period = target_period
        self._emission_registry = emission_registry
        self.__consumer_mapper = ConsumerMapper(
            references=references, target_period=target_period, emission_registry=emission_registry
        )

    def from_yaml_to_domain(
        self,
        data: YamlGeneratorSet,
        regularity: Regularity,
        expression_evaluator: ExpressionEvaluator,
        configuration: YamlValidator,
        yaml_path: YamlPath,
        mapping_context: MappingContext,
        parent_id: PathID,
        default_fuel: str | None = None,
    ) -> GeneratorSetEnergyComponent:
        def create_error(message: str, key: str) -> ModelValidationError:
            file_context = configuration.get_file_context(yaml_path.keys)
            return ModelValidationError(
                message=message,
                location=mapping_context.get_location_from_yaml_path(yaml_path.append(key)),
                name=data.name,
                file_context=file_context,
            )

        generator_set_id = PathID(data.name)
        fuel = _resolve_fuel(data.fuel, default_fuel, self.__references, target_period=self._target_period)
        try:
            fuel_consumer_emitter = FuelConsumerEmitter(
                entity_id=generator_set_id,
                emissions=TemporalEmissionFactors(expression_evaluator=expression_evaluator, temporal_fuel=fuel),
            )
            self._emission_registry.add_emitter(fuel_consumer_emitter, parent_container_id=parent_id)
        except InvalidReferenceException as e:
            raise ComponentValidationException(errors=[create_error(str(e), key="fuel")]) from e
        except MissingFuelReference as e:
            raise ComponentValidationException(errors=[create_error(str(e), key="fuel")]) from e
        except InvalidTemporalModel as e:
            raise ComponentValidationException(errors=[create_error(str(e), key="fuel")]) from e

        generator_set_model_data = define_time_model_for_period(
            data.electricity2fuel, target_period=self._target_period
        )

        try:
            generator_set_model = TemporalModel(
                {
                    start_time: self.__references.get_generator_set_model(model_reference)
                    for start_time, model_reference in generator_set_model_data.items()
                }
            )
        except InvalidReferenceException as e:
            raise ComponentValidationException(errors=[create_error(str(e), key="ELECTRICITY2FUEL")]) from e
        except InvalidTemporalModel as e:
            raise ComponentValidationException(errors=[create_error(str(e), key="ELECTRICITY2FUEL")]) from e

        consumers_yaml_path = yaml_path.append("CONSUMERS")
        consumers: list[ElectricityConsumer] = []
        for consumer_index, consumer in enumerate(data.consumers):
            consumer_yaml_path = consumers_yaml_path.append(consumer_index)
            mapping_context.register_component_name(consumer_yaml_path, consumer.name)
            mapped_consumer = self.__consumer_mapper.from_yaml_to_domain(
                consumer,
                regularity=regularity,
                consumes=ConsumptionType.ELECTRICITY,
                expression_evaluator=expression_evaluator,
                configuration=configuration,
                yaml_path=consumer_yaml_path,
                mapping_context=mapping_context,
                parent_id=generator_set_id,
            )
            assert isinstance(mapped_consumer, ElectricityConsumer)
            consumers.append(mapped_consumer)
        user_defined_category = define_time_model_for_period(data.category, target_period=self._target_period)

        cable_loss = convert_expression(data.cable_loss)
        max_usage_from_shore = convert_expression(data.max_usage_from_shore)

        return GeneratorSetEnergyComponent(
            path_id=generator_set_id,
            regularity=regularity,
            generator_set_model=generator_set_model,
            consumers=consumers,
            temporal_fuel=TemporalModel(
                {period: Fuel(name=fuel.name, category=fuel.category) for period, fuel in fuel.items()}
            ),
            user_defined_category=user_defined_category,  # type: ignore[arg-type]
            cable_loss=cable_loss,  # type: ignore[arg-type]
            max_usage_from_shore=max_usage_from_shore,  # type: ignore[arg-type]
            component_type=ComponentType.GENERATOR_SET,
            expression_evaluator=expression_evaluator,
        )


class InstallationMapper:
    def __init__(
        self,
        references: ReferenceService,
        target_period: Period,
        emission_registry: EmissionRegistry,
        storage_registry: list[StorageContainer],
    ):
        self.__references = references
        self._target_period = target_period
        self._emission_registry = emission_registry
        self.__generator_set_mapper = GeneratorSetMapper(
            references=references,
            target_period=target_period,
            emission_registry=emission_registry,
        )
        self.__consumer_mapper = ConsumerMapper(
            references=references,
            target_period=target_period,
            emission_registry=emission_registry,
        )
        self._storage_registry = storage_registry

    def from_yaml_venting_emitter_to_domain(
        self,
        data: YamlDirectTypeEmitter | YamlOilTypeEmitter,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
        configuration: YamlValidator,
        yaml_path: YamlPath,
        mapping_context: MappingContext,
    ) -> tuple[DirectVentingEmitter | OilVentingEmitter, StorageContainer | None]:
        venting_emitter_id = PathID(data.name)
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
                path_id=venting_emitter_id,
                expression_evaluator=expression_evaluator,
                emissions=emissions,
                regularity=regularity,
            ), None
        else:
            assert isinstance(data, YamlOilTypeEmitter)
            storage_container = OilStorageContainer(
                regularity=regularity,
                path_id=venting_emitter_id,
                expression_evaluator=expression_evaluator,
                oil_volume_rate=OilVolumeRate(
                    value=data.volume.rate.value,
                    unit=data.volume.rate.unit.to_unit(),
                    rate_type=data.volume.rate.type,
                ),
            )
            self._storage_registry.append(storage_container)
            return (
                OilVentingEmitter(
                    path_id=venting_emitter_id,
                    expression_evaluator=expression_evaluator,
                    emissions=[
                        VentingVolumeEmission(name=emission.name, emission_factor=emission.emission_factor)
                        for emission in data.volume.emissions
                    ],
                    regularity=regularity,
                ),
                storage_container,
            )

    def from_yaml_to_domain(
        self,
        data: YamlInstallation,
        expression_evaluator: ExpressionEvaluator,
        configuration: YamlValidator,
        yaml_path: YamlPath,
        mapping_context: MappingContext,
        parent_id: PathID,
    ) -> Installation:
        def create_error(message: str, key: str) -> ModelValidationError:
            file_context = configuration.get_file_context(yaml_path.keys)
            return ModelValidationError(
                message=message,
                location=mapping_context.get_location_from_yaml_path(yaml_path.append(key)),
                name=data.name,
                file_context=file_context,
            )

        fuel_data = data.fuel
        installation_id = PathID(data.name)

        try:
            regularity = Regularity(
                expression_input=data.regularity,
                target_period=self._target_period,
                expression_evaluator=expression_evaluator,
            )
        except InvalidRegularity as e:
            raise ComponentValidationException(errors=[create_error(message=e.message, key="regularity")]) from e

        try:
            hydrocarbon_export = HydrocarbonExport(
                expression_input=data.hydrocarbon_export,
                expression_evaluator=expression_evaluator,
                regularity=regularity,
                target_period=self._target_period,
            )
        except InvalidHydrocarbonExport as e:
            raise ComponentValidationException(errors=[create_error(message=e.message, key="HCEXPORT")]) from e

        generator_sets_yaml_path = yaml_path.append("GENERATORSETS")
        generator_sets = []
        for generator_set_index, generator_set in enumerate(data.generator_sets or []):
            generator_set_yaml_path = generator_sets_yaml_path.append(generator_set_index)
            mapping_context.register_component_name(generator_set_yaml_path, generator_set.name)
            generator_sets.append(
                self.__generator_set_mapper.from_yaml_to_domain(
                    generator_set,
                    regularity=regularity,
                    default_fuel=fuel_data,  # type: ignore[arg-type]
                    expression_evaluator=expression_evaluator,
                    configuration=configuration,
                    yaml_path=generator_set_yaml_path,
                    mapping_context=mapping_context,
                    parent_id=installation_id,
                )
            )

        fuel_consumers_yaml_path = yaml_path.append("FUELCONSUMERS")
        fuel_consumers = []
        for fuel_consumer_index, fuel_consumer in enumerate(data.fuel_consumers or []):
            fuel_consumer_yaml_path = fuel_consumers_yaml_path.append(fuel_consumer_index)
            mapping_context.register_component_name(fuel_consumer_yaml_path, fuel_consumer.name)
            fuel_consumers.append(
                self.__consumer_mapper.from_yaml_to_domain(
                    fuel_consumer,
                    regularity=regularity,
                    consumes=ConsumptionType.FUEL,
                    default_fuel=fuel_data,  # type: ignore[arg-type]
                    expression_evaluator=expression_evaluator,
                    configuration=configuration,
                    yaml_path=fuel_consumer_yaml_path,
                    mapping_context=mapping_context,
                    parent_id=installation_id,
                )
            )

        venting_emitter_components: list[VentingEmitterComponent] = []
        installation_storage_containers: list[StorageContainer] = []
        venting_emitters_yaml_path = yaml_path.append("VENTING_EMITTERS")
        for venting_emitter_index, venting_emitter in enumerate(data.venting_emitters or []):
            venting_emitter_yaml_path = venting_emitters_yaml_path.append(venting_emitter_index)
            mapping_context.register_component_name(venting_emitter_yaml_path, venting_emitter.name)
            parsed_venting_emitter, storage_container = self.from_yaml_venting_emitter_to_domain(
                venting_emitter,
                expression_evaluator=expression_evaluator,
                regularity=regularity,
                configuration=configuration,
                yaml_path=venting_emitter_yaml_path,
                mapping_context=mapping_context,
            )
            self._emission_registry.add_emitter(parsed_venting_emitter, parent_container_id=installation_id)

            if storage_container is not None:
                self._storage_registry.append(storage_container)
                installation_storage_containers.append(storage_container)

            venting_emitter_components.append(
                VentingEmitterComponent(
                    path_id=parsed_venting_emitter.get_id(),
                    user_defined_category=venting_emitter.category,
                    emitter_type=venting_emitter.type,
                )
            )

        self._emission_registry.add_container(
            EmissionContainer(
                entity_id=installation_id,
                parent_container=parent_id,
            )
        )
        return Installation(
            path_id=installation_id,
            regularity=regularity,
            hydrocarbon_export=hydrocarbon_export,
            fuel_consumers=[*generator_sets, *fuel_consumers],  # type: ignore[list-item]
            storage_containers=installation_storage_containers,
            venting_emitters=venting_emitter_components,
            user_defined_category=data.category,
            expression_evaluator=expression_evaluator,
        )


class EcalcModelMapper:
    def __init__(
        self,
        references: ReferenceService,
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
        emission_registry: EmissionRegistry,
        storage_registry: list[StorageContainer],
    ):
        self.__references = references
        self._emission_registry = emission_registry
        self.__installation_mapper = InstallationMapper(
            references=references,
            target_period=target_period,
            emission_registry=emission_registry,
            storage_registry=storage_registry,
        )
        self.__expression_evaluator = expression_evaluator
        self.__mapping_context = MappingContext()

    def from_yaml_to_domain(self, configuration: YamlValidator) -> Asset:
        installations_path = YamlPath(("installations",))
        try:
            asset_id = PathID(configuration.name)
            installations = []
            for installation_index, installation in enumerate(configuration.installations):
                installation_yaml_path = installations_path.append(installation_index)
                self.__mapping_context.register_component_name(installation_yaml_path, installation.name)
                installations.append(
                    self.__installation_mapper.from_yaml_to_domain(
                        installation,
                        expression_evaluator=self.__expression_evaluator,
                        configuration=configuration,
                        yaml_path=installation_yaml_path,
                        mapping_context=self.__mapping_context,
                        parent_id=asset_id,
                    )
                )
            ecalc_model = Asset(
                path_id=asset_id,
                installations=installations,
            )
            self._emission_registry.add_container(EmissionContainer(entity_id=asset_id))
            return ecalc_model
        except ValidationError as e:
            raise DtoValidationError(data=None, validation_error=e) from e
