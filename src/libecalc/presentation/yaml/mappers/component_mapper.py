from typing import assert_never
from uuid import UUID, uuid4

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
from libecalc.domain.infrastructure.energy_components.common import Consumer
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumerComponent
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.installation.installation import InstallationComponent
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import InvalidRegularity, Regularity
from libecalc.dto import FuelType
from libecalc.expression.expression import InvalidExpressionError
from libecalc.presentation.yaml.domain.expression_time_series_cable_loss import ExpressionTimeSeriesCableLoss
from libecalc.presentation.yaml.domain.expression_time_series_max_usage_from_shore import (
    ExpressionTimeSeriesMaxUsageFromShore,
)
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException, ReferenceService
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.domain.yaml_component import YamlComponent
from libecalc.presentation.yaml.mappers.consumer_function_mapper import (
    ConsumerFunctionMapper,
    InvalidEnergyUsageModelException,
)
from libecalc.presentation.yaml.mappers.yaml_mapping_context import MappingContext
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.validation_errors import DtoValidationError, Location
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


def get_location_from_yaml_path(yaml_path: YamlPath, mapping_context: MappingContext):
    """
    Replace indices with names of the objects to create a Location, which is displayed to user
    """
    location_keys = []

    current_path = YamlPath()

    for key in yaml_path.keys:
        current_path = current_path.append(key)
        if isinstance(key, int):
            location_keys.append(mapping_context.get_component_name_from_yaml_path(current_path) or key)
        else:
            location_keys.append(key)

    return Location(keys=location_keys)


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
    mapping_context: MappingContext,
    yaml_path: YamlPath,
) -> dict[Period, FuelType]:
    fuel = consumer_fuel or default_fuel  # Use parent fuel only if not specified on this consumer

    if fuel is None:
        raise MissingFuelReference()

    time_adjusted_fuel = define_time_model_for_period(fuel, target_period=target_period)

    temporal_fuel_model = {}
    for period, fuel in time_adjusted_fuel.items():
        resolved_fuel = references.get_fuel_reference(fuel)  # type: ignore[arg-type]
        mapping_context.register_yaml_component(
            yaml_path=yaml_path,
            path_id=PathID(resolved_fuel.name),
            yaml_component=YamlComponent(
                id=resolved_fuel.id,
                name=resolved_fuel.name,
                category=resolved_fuel.user_defined_category,
            ),
        )

        temporal_fuel_model[period] = resolved_fuel

    return temporal_fuel_model


class ConsumerMapper:
    def __init__(self, references: ReferenceService, target_period: Period):
        self.__references = references
        self._target_period = target_period

    def from_yaml_to_domain(
        self,
        data: YamlFuelConsumer | YamlElectricityConsumer,
        id: UUID,
        path_id: PathID,
        regularity: Regularity,
        consumes: ConsumptionType,
        expression_evaluator: ExpressionEvaluator,
        configuration: YamlValidator,
        yaml_path: YamlPath,
        mapping_context: MappingContext,
        default_fuel: str | None = None,
    ) -> Consumer | None:
        energy_usage_model_mapper = ConsumerFunctionMapper(
            references=self.__references,
            target_period=self._target_period,
            expression_evaluator=expression_evaluator,
            regularity=regularity,
            energy_usage_model=data.energy_usage_model,
        )

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
                location=get_location_from_yaml_path(key_path, mapping_context=mapping_context),
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
                location=get_location_from_yaml_path(specific_path, mapping_context=mapping_context),
                name=data.name,
                file_context=file_context,
            )

        try:
            energy_usage_model = energy_usage_model_mapper.from_yaml_to_dto(
                consumes=consumes,
            )
            if energy_usage_model is None:
                return None
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

        if consumes == ConsumptionType.FUEL:
            consumer_fuel = data.fuel
            fuel_yaml_path = yaml_path.append("fuel")
            try:
                fuel = TemporalModel(
                    _resolve_fuel(
                        consumer_fuel,
                        default_fuel,
                        self.__references,
                        target_period=self._target_period,
                        mapping_context=mapping_context,
                        yaml_path=fuel_yaml_path,
                    )
                )
            except (InvalidReferenceException, MissingFuelReference, InvalidTemporalModel) as e:
                raise ComponentValidationException(
                    errors=[create_error_from_yaml_path(message=str(e), specific_path=fuel_yaml_path)]
                ) from e

            return FuelConsumerComponent(
                id=id,
                path_id=path_id,
                regularity=regularity,
                fuel=fuel,
                energy_usage_model=energy_usage_model,
                component_type=_get_component_type(data.energy_usage_model),
                expression_evaluator=expression_evaluator,
            )
        else:
            return ElectricityConsumer(
                id=id,
                path_id=path_id,
                regularity=regularity,
                energy_usage_model=energy_usage_model,
                component_type=_get_component_type(data.energy_usage_model),
                consumes=consumes,
                expression_evaluator=expression_evaluator,
            )


class GeneratorSetMapper:
    def __init__(self, references: ReferenceService, target_period: Period):
        self.__references = references
        self._target_period = target_period
        self.__consumer_mapper = ConsumerMapper(references=references, target_period=target_period)

    def from_yaml_to_domain(
        self,
        data: YamlGeneratorSet,
        id: UUID,
        path_id: PathID,
        regularity: Regularity,
        expression_evaluator: ExpressionEvaluator,
        configuration: YamlValidator,
        yaml_path: YamlPath,
        mapping_context: MappingContext,
        default_fuel: str | None = None,
    ) -> GeneratorSetEnergyComponent | None:
        def create_error(message: str, key: str) -> ModelValidationError:
            file_context = configuration.get_file_context(yaml_path.keys)
            return ModelValidationError(
                message=message,
                location=get_location_from_yaml_path(yaml_path.append(key), mapping_context=mapping_context),
                name=data.name,
                file_context=file_context,
            )

        fuel_yaml_path = yaml_path.append("fuel")
        try:
            fuel = TemporalModel(
                _resolve_fuel(
                    data.fuel,
                    default_fuel,
                    self.__references,
                    target_period=self._target_period,
                    mapping_context=mapping_context,
                    yaml_path=fuel_yaml_path,
                )
            )
        except (InvalidReferenceException, MissingFuelReference, InvalidTemporalModel) as e:
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
            consumer_path_id = PathID(consumer.name)
            consumer_id = uuid4()
            mapping_context.register_yaml_component(
                yaml_path=consumer_yaml_path,
                path_id=consumer_path_id,
                yaml_component=YamlComponent(
                    id=consumer_id,
                    name=consumer.name,
                    category=consumer.category,  # type: ignore[arg-type]
                ),
            )
            parsed_consumer = self.__consumer_mapper.from_yaml_to_domain(
                consumer,
                id=consumer_id,
                path_id=consumer_path_id,
                regularity=regularity,
                consumes=ConsumptionType.ELECTRICITY,
                expression_evaluator=expression_evaluator,
                configuration=configuration,
                yaml_path=consumer_yaml_path,
                mapping_context=mapping_context,
            )

            if parsed_consumer is None:
                # Skip None consumer, filtered based on start date
                continue

            assert isinstance(parsed_consumer, ElectricityConsumer)
            consumers.append(parsed_consumer)

        try:
            category_model = TemporalModel.create(data.category, target_period=self._target_period)
            if data.cable_loss and category_model is not None:
                cable_loss = ExpressionTimeSeriesCableLoss(
                    time_series_expression=TimeSeriesExpression(
                        expressions=data.cable_loss, expression_evaluator=expression_evaluator
                    ),
                    category=category_model,
                )
            else:
                cable_loss = None

        except InvalidExpressionError as e:
            raise ComponentValidationException(errors=[create_error(str(e), key="CABLE_LOSS")]) from e

        try:
            max_usage_from_shore = (
                ExpressionTimeSeriesMaxUsageFromShore(
                    TimeSeriesExpression(
                        expressions=data.max_usage_from_shore, expression_evaluator=expression_evaluator
                    )
                )
                if data.max_usage_from_shore
                else None
            )
        except InvalidExpressionError as e:
            raise ComponentValidationException(errors=[create_error(str(e), key="MAX_USAGE_FROM_SHORE")]) from e

        return GeneratorSetEnergyComponent(
            id=id,
            path_id=path_id,
            fuel=fuel,
            regularity=regularity,
            generator_set_model=generator_set_model,
            consumers=consumers,
            cable_loss=cable_loss,
            max_usage_from_shore=max_usage_from_shore,
            component_type=ComponentType.GENERATOR_SET,
            expression_evaluator=expression_evaluator,
        )


class InstallationMapper:
    def __init__(self, references: ReferenceService, target_period: Period):
        self.__references = references
        self._target_period = target_period
        self.__generator_set_mapper = GeneratorSetMapper(references=references, target_period=target_period)
        self.__consumer_mapper = ConsumerMapper(references=references, target_period=target_period)

    def from_yaml_venting_emitter_to_domain(
        self,
        data: YamlDirectTypeEmitter | YamlOilTypeEmitter,
        id: UUID,
        path_id: PathID,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
        configuration: YamlValidator,
        yaml_path: YamlPath,
        mapping_context: MappingContext,
    ) -> DirectVentingEmitter | OilVentingEmitter:
        venting_emitter_location = get_location_from_yaml_path(yaml_path, mapping_context=mapping_context)

        def create_error(message: str) -> ModelValidationError:
            file_context = configuration.get_file_context(yaml_path.keys)
            return ModelValidationError(
                message=message,
                location=venting_emitter_location,
                name=data.name,
                file_context=file_context,
            )

        try:
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
                    id=id,
                    path_id=path_id,
                    expression_evaluator=expression_evaluator,
                    component_type=data.component_type,
                    emitter_type=data.type,
                    emissions=emissions,
                    regularity=regularity,
                )
            elif isinstance(data, YamlOilTypeEmitter):
                return OilVentingEmitter(
                    id=id,
                    path_id=path_id,
                    expression_evaluator=expression_evaluator,
                    component_type=data.component_type,
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
                return assert_never(data)
        except InvalidExpressionError as e:
            raise ComponentValidationException(errors=[create_error(message=str(e))]) from e

    def from_yaml_to_domain(
        self,
        data: YamlInstallation,
        id: UUID,
        path_id: PathID,
        expression_evaluator: ExpressionEvaluator,
        configuration: YamlValidator,
        yaml_path: YamlPath,
        mapping_context: MappingContext,
    ) -> InstallationComponent:
        def create_error(message: str, key: str) -> ModelValidationError:
            file_context = configuration.get_file_context(yaml_path.keys)
            return ModelValidationError(
                message=message,
                location=get_location_from_yaml_path(yaml_path.append(key), mapping_context=mapping_context),
                name=data.name,
                file_context=file_context,
            )

        fuel_data = data.fuel

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
            generator_set_path_id = PathID(generator_set.name)
            generator_set_id = uuid4()
            mapping_context.register_yaml_component(
                yaml_path=generator_set_yaml_path,
                path_id=generator_set_path_id,
                yaml_component=YamlComponent(
                    id=generator_set_id,
                    name=generator_set.name,
                    category=generator_set.category,  # type: ignore[arg-type]
                ),
            )
            parsed_generator_set = self.__generator_set_mapper.from_yaml_to_domain(
                generator_set,
                id=generator_set_id,
                path_id=generator_set_path_id,
                regularity=regularity,
                default_fuel=fuel_data,  # type: ignore[arg-type]
                expression_evaluator=expression_evaluator,
                configuration=configuration,
                yaml_path=generator_set_yaml_path,
                mapping_context=mapping_context,
            )

            generator_sets.append(parsed_generator_set)

        fuel_consumers_yaml_path = yaml_path.append("FUELCONSUMERS")
        fuel_consumers = []
        for fuel_consumer_index, fuel_consumer in enumerate(data.fuel_consumers or []):
            fuel_consumer_yaml_path = fuel_consumers_yaml_path.append(fuel_consumer_index)
            fuel_consumer_path_id = PathID(fuel_consumer.name)
            fuel_consumer_id = uuid4()
            mapping_context.register_yaml_component(
                yaml_path=fuel_consumer_yaml_path,
                path_id=fuel_consumer_path_id,
                yaml_component=YamlComponent(
                    id=fuel_consumer_id,
                    name=fuel_consumer.name,
                    category=fuel_consumer.category,  # type: ignore[arg-type]
                ),
            )
            parsed_fuel_consumer = self.__consumer_mapper.from_yaml_to_domain(
                fuel_consumer,
                id=fuel_consumer_id,
                path_id=fuel_consumer_path_id,
                regularity=regularity,
                consumes=ConsumptionType.FUEL,
                default_fuel=fuel_data,  # type: ignore[arg-type]
                expression_evaluator=expression_evaluator,
                configuration=configuration,
                yaml_path=fuel_consumer_yaml_path,
                mapping_context=mapping_context,
            )
            if parsed_fuel_consumer is None:
                # Skip None consumer, filtered based on start date
                continue
            fuel_consumers.append(parsed_fuel_consumer)

        venting_emitters_yaml_path = yaml_path.append("VENTING_EMITTERS")
        venting_emitters = []
        for venting_emitter_index, venting_emitter in enumerate(data.venting_emitters or []):
            venting_emitter_yaml_path = venting_emitters_yaml_path.append(venting_emitter_index)
            venting_emitter_path_id = PathID(venting_emitter.name)
            venting_emitter_id = uuid4()
            mapping_context.register_yaml_component(
                yaml_path=venting_emitter_yaml_path,
                path_id=venting_emitter_path_id,
                yaml_component=YamlComponent(
                    id=venting_emitter_id,
                    name=venting_emitter.name,
                    category=venting_emitter.category,
                ),
            )
            parsed_venting_emitter = self.from_yaml_venting_emitter_to_domain(
                venting_emitter,
                id=venting_emitter_id,
                path_id=venting_emitter_path_id,
                expression_evaluator=expression_evaluator,
                regularity=regularity,
                configuration=configuration,
                yaml_path=venting_emitter_yaml_path,
                mapping_context=mapping_context,
            )
            venting_emitters.append(parsed_venting_emitter)

        return InstallationComponent(
            id=id,
            path_id=path_id,
            regularity=regularity,
            hydrocarbon_export=hydrocarbon_export,
            fuel_consumers=[*generator_sets, *fuel_consumers],  # type: ignore[list-item]
            venting_emitters=venting_emitters,  # type: ignore[arg-type]
            expression_evaluator=expression_evaluator,
        )


class EcalcModelMapper:
    def __init__(
        self,
        references: ReferenceService,
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
        mapping_context: MappingContext,
    ):
        self.__references = references
        self.__installation_mapper = InstallationMapper(references=references, target_period=target_period)
        self.__expression_evaluator = expression_evaluator
        self.__mapping_context = mapping_context

    def from_yaml_to_domain(self, configuration: YamlValidator) -> Asset:
        installations_path = YamlPath(("installations",))
        try:
            installations = []
            for installation_index, installation in enumerate(configuration.installations):
                installation_yaml_path = installations_path.append(installation_index)
                installation_path_id = PathID(installation.name)
                installation_id = uuid4()
                self.__mapping_context.register_yaml_component(
                    yaml_path=installation_yaml_path,
                    path_id=installation_path_id,
                    yaml_component=YamlComponent(
                        id=installation_id,
                        name=installation.name,
                        category=installation.category,
                    ),
                )
                parsed_installation = self.__installation_mapper.from_yaml_to_domain(
                    installation,
                    id=installation_id,
                    path_id=installation_path_id,
                    expression_evaluator=self.__expression_evaluator,
                    configuration=configuration,
                    yaml_path=installation_yaml_path,
                    mapping_context=self.__mapping_context,
                )

                installations.append(parsed_installation)
            ecalc_model = Asset(
                id=uuid4(),
                path_id=PathID(configuration.name),
                installations=installations,
            )
            return ecalc_model
        except ValidationError as e:
            raise DtoValidationError(data=None, validation_error=e) from e
