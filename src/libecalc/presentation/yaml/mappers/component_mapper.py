import uuid
from dataclasses import dataclass
from typing import assert_never, overload

from pydantic import ValidationError

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.temporal_model import InvalidTemporalModel, TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.energy import EnergyComponent
from libecalc.domain.energy.energy_component import EnergyContainerID
from libecalc.domain.hydrocarbon_export import HydrocarbonExport
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
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumerComponent
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.installation.installation import InstallationComponent
from libecalc.domain.regularity import Regularity
from libecalc.domain.resource import Resource, Resources
from libecalc.dto import Emission, FuelType
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
from libecalc.presentation.yaml.mappers.facility_input import _get_adjustment_constant, _get_adjustment_factor
from libecalc.presentation.yaml.mappers.yaml_mapping_context import MappingContext
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.validation_errors import Location, ModelValidationError
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


@dataclass
class Defaults:
    regularity: Regularity = None
    fuel: YamlTemporalModel[str] = None


class EcalcModelMapper:
    def __init__(
        self,
        resources: Resources,
        references: ReferenceService,
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
        mapping_context: MappingContext,
        configuration: YamlValidator,
    ):
        self._resources = resources
        self._references = references
        self._target_period = target_period
        self._expression_evaluator = expression_evaluator
        self._mapping_context = mapping_context
        self._configuration = configuration

    def _create_error(
        self,
        message: str,
        specific_path: YamlPath,
    ):
        file_context = self._configuration.get_file_context(specific_path.keys)

        return ModelValidationError(
            message=message,
            location=get_location_from_yaml_path(specific_path, mapping_context=self._mapping_context),
            file_context=file_context,
        )

    def _create_reference_error(self, message: str, reference: str, key: str | None = None):
        yaml_path = self._references.get_yaml_path(reference)

        location_keys = [*yaml_path.keys[:-1], reference]  # Replace index with name

        if key is not None:
            key_path = yaml_path.append(key)
            location_keys.append(key)
        else:
            key_path = yaml_path

        file_context = self._configuration.get_file_context(key_path.keys)
        return ModelValidationError(
            message=message,
            location=Location(keys=location_keys),
            name=reference,
            file_context=file_context,
        )

    def _get_resource(self, resource_name: str, reference: str) -> Resource:
        resource = self._resources.get(resource_name)
        if resource is None:
            raise ModelValidationException(
                errors=[
                    self._create_reference_error(
                        message=f"Unable to find resource '{resource_name}'", reference=reference, key="FILE"
                    )
                ]
            )
        return resource

    def _resolve_fuel(
        self,
        consumer_fuel: YamlTemporalModel[str] | None,
        default_fuel: YamlTemporalModel[str] | None,
    ) -> dict[Period, FuelType]:
        fuel = consumer_fuel or default_fuel  # Use parent fuel only if not specified on this consumer

        if fuel is None:
            raise MissingFuelReference()

        time_adjusted_fuel = define_time_model_for_period(fuel, target_period=self._target_period)

        temporal_fuel_model = {}
        for period, fuel in time_adjusted_fuel.items():
            assert isinstance(fuel, str)
            resolved_fuel = self._references.get_fuel_reference(fuel)
            yaml_path = self._references.get_yaml_path(fuel)
            fuel_id = uuid.uuid4()
            self._mapping_context.register_yaml_component(
                yaml_path=yaml_path,
                yaml_component=YamlComponent(
                    id=fuel_id,
                    name=resolved_fuel.name,
                    category=resolved_fuel.category,
                ),
            )
            try:
                parsed_fuel = FuelType(
                    id=fuel_id,
                    name=resolved_fuel.name,
                    user_defined_category=resolved_fuel.category,
                    emissions=[
                        Emission(
                            name=emission.name,
                            factor=emission.factor,
                        )
                        for emission in resolved_fuel.emissions
                    ],
                )
            except ValidationError as e:
                raise ModelValidationException.from_pydantic(
                    e, file_context=self._configuration.get_file_context(yaml_path.keys)
                ) from e
            except (InvalidExpressionError, DomainValidationException) as e:
                raise ModelValidationException(errors=[self._create_error(str(e), specific_path=yaml_path)]) from e

            temporal_fuel_model[period] = parsed_fuel

        return temporal_fuel_model

    def _create_generator_set_model(self, reference: str) -> GeneratorSetModel:
        model = self._references.get_generator_set_model(reference)
        resource = self._get_resource(model.file, reference)
        adjustment_constant = _get_adjustment_constant(model)
        adjustment_factor = _get_adjustment_factor(model)

        try:
            return GeneratorSetModel(
                name=model.name,
                resource=resource,
                energy_usage_adjustment_constant=adjustment_constant,
                energy_usage_adjustment_factor=adjustment_factor,
            )
        except DomainValidationException as e:
            raise ModelValidationException(
                errors=[self._create_reference_error(message=str(e), reference=reference)]
            ) from e

    def map_generator_set(
        self,
        data: YamlGeneratorSet,
        id: uuid.UUID,
        yaml_path: YamlPath,
        defaults: Defaults,
    ):
        assert defaults.regularity is not None
        fuel_yaml_path = yaml_path.append("fuel")
        try:
            fuel = TemporalModel(
                self._resolve_fuel(
                    data.fuel,
                    defaults.fuel,
                )
            )
        except (InvalidReferenceException, MissingFuelReference, InvalidTemporalModel) as e:
            raise ModelValidationException(errors=[self._create_error(str(e), specific_path=fuel_yaml_path)]) from e

        generator_set_model_data = define_time_model_for_period(
            data.electricity2fuel, target_period=self._target_period
        )

        try:
            generator_set_model = TemporalModel(
                {
                    start_time: self._create_generator_set_model(model_reference)
                    for start_time, model_reference in generator_set_model_data.items()
                }
            )
        except (InvalidReferenceException, InvalidTemporalModel, DomainValidationException) as e:
            raise ModelValidationException(
                errors=[self._create_error(str(e), specific_path=yaml_path.append("ELECTRICITY2FUEL"))]
            ) from e

        consumers_yaml_path = yaml_path.append("CONSUMERS")
        consumers: list[ElectricityConsumer] = []
        for consumer_index, consumer in enumerate(data.consumers):
            consumer_yaml_path = consumers_yaml_path.append(consumer_index)
            consumer_id = uuid.uuid4()
            parsed_consumer = self.map_yaml_component(
                consumer, id=consumer_id, yaml_path=consumer_yaml_path, parent=id, defaults=defaults
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
                        expression=data.cable_loss, expression_evaluator=self._expression_evaluator
                    ),
                    category=category_model,
                )
            else:
                cable_loss = None

        except (InvalidExpressionError, DomainValidationException) as e:
            raise ModelValidationException(
                errors=[self._create_error(str(e), specific_path=yaml_path.append("CABLE_LOSS"))]
            ) from e

        try:
            max_usage_from_shore = (
                ExpressionTimeSeriesMaxUsageFromShore(
                    TimeSeriesExpression(
                        expression=data.max_usage_from_shore, expression_evaluator=self._expression_evaluator
                    )
                )
                if data.max_usage_from_shore
                else None
            )
        except (InvalidExpressionError, DomainValidationException) as e:
            raise ModelValidationException(
                errors=[self._create_error(str(e), specific_path=yaml_path.append("MAX_USAGE_FROM_SHORE"))]
            ) from e

        try:
            return GeneratorSetEnergyComponent(
                id=id,
                name=data.name,
                fuel=fuel,
                regularity=defaults.regularity,
                generator_set_model=generator_set_model,
                consumers=consumers,
                cable_loss=cable_loss,
                max_usage_from_shore=max_usage_from_shore,
                component_type=ComponentType.GENERATOR_SET,
                expression_evaluator=self._expression_evaluator,
            )
        except DomainValidationException as e:
            raise ModelValidationException(errors=[self._create_error(str(e), specific_path=yaml_path)]) from e

    def map_installation(
        self,
        data: YamlInstallation,
        id: uuid.UUID,
        yaml_path: YamlPath,
        defaults: Defaults = None,
    ) -> InstallationComponent:
        try:
            regularity = Regularity(
                expression_input=data.regularity,
                target_period=self._target_period,
                expression_evaluator=self._expression_evaluator,
            )
        except DomainValidationException as e:
            raise ModelValidationException(
                errors=[self._create_error(message=e.message, specific_path=yaml_path.append("regularity"))]
            ) from e

        defaults = Defaults(
            fuel=data.fuel,
            regularity=regularity,
        )

        try:
            hydrocarbon_export = HydrocarbonExport(
                expression_input=data.hydrocarbon_export,
                expression_evaluator=self._expression_evaluator,
                regularity=regularity,
                target_period=self._target_period,
            )
        except DomainValidationException as e:
            raise ModelValidationException(
                errors=[self._create_error(message=e.message, specific_path=yaml_path.append("HCEXPORT"))]
            ) from e

        generator_sets_yaml_path = yaml_path.append("GENERATORSETS")
        generator_sets = []
        for generator_set_index, generator_set in enumerate(data.generator_sets or []):
            generator_set_yaml_path = generator_sets_yaml_path.append(generator_set_index)
            generator_set_id = uuid.uuid4()
            parsed_generator_set = self.map_yaml_component(
                generator_set,
                id=generator_set_id,
                yaml_path=generator_set_yaml_path,
                parent=id,
                defaults=defaults,
            )
            generator_sets.append(parsed_generator_set)

        fuel_consumers_yaml_path = yaml_path.append("FUELCONSUMERS")
        fuel_consumers = []
        for fuel_consumer_index, fuel_consumer in enumerate(data.fuel_consumers or []):
            fuel_consumer_yaml_path = fuel_consumers_yaml_path.append(fuel_consumer_index)
            fuel_consumer_id = uuid.uuid4()
            parsed_fuel_consumer = self.map_yaml_component(
                fuel_consumer,
                id=fuel_consumer_id,
                yaml_path=fuel_consumer_yaml_path,
                parent=id,
                defaults=defaults,
            )
            if parsed_fuel_consumer is None:
                # Skip None consumer, filtered based on start date
                continue
            fuel_consumers.append(parsed_fuel_consumer)

        venting_emitters_yaml_path = yaml_path.append("VENTING_EMITTERS")
        venting_emitters = []
        for venting_emitter_index, venting_emitter in enumerate(data.venting_emitters or []):
            venting_emitter_yaml_path = venting_emitters_yaml_path.append(venting_emitter_index)
            venting_emitter_id = uuid.uuid4()
            parsed_venting_emitter = self.map_yaml_component(
                venting_emitter,
                id=venting_emitter_id,
                yaml_path=venting_emitter_yaml_path,
                parent=id,
                defaults=defaults,
            )
            venting_emitters.append(parsed_venting_emitter)

        try:
            return InstallationComponent(
                id=id,
                name=data.name,
                regularity=regularity,
                hydrocarbon_export=hydrocarbon_export,
                fuel_consumers=[*generator_sets, *fuel_consumers],
                venting_emitters=venting_emitters,  # type: ignore[arg-type]
                expression_evaluator=self._expression_evaluator,
            )
        except DomainValidationException as e:
            raise ModelValidationException(errors=[self._create_error(str(e), specific_path=yaml_path)]) from e

    def map_consumer(
        self, data: YamlElectricityConsumer | YamlFuelConsumer, id: uuid.UUID, yaml_path: YamlPath, defaults: Defaults
    ) -> FuelConsumerComponent | ElectricityConsumer:
        assert defaults.regularity is not None
        energy_usage_model_mapper = ConsumerFunctionMapper(
            configuration=self._configuration,
            resources=self._resources,
            references=self._references,
            target_period=self._target_period,
            expression_evaluator=self._expression_evaluator,
            regularity=defaults.regularity,
            energy_usage_model=data.energy_usage_model,
            mapping_context=self._mapping_context,
            consumer_id=id,
        )

        consumes = ConsumptionType.ELECTRICITY if isinstance(data, YamlElectricityConsumer) else ConsumptionType.FUEL

        try:
            energy_usage_model = energy_usage_model_mapper.from_yaml_to_dto(
                consumes=consumes,
            )
            if energy_usage_model is None:
                return None
        except InvalidEnergyUsageModelException as e:
            energy_usage_model_yaml_path = yaml_path.append("ENERGY_USAGE_MODEL")
            specific_model_path = energy_usage_model_yaml_path.append(e.period.start)
            raise ModelValidationException(
                errors=[
                    self._create_error(
                        message=e.message,
                        specific_path=specific_model_path,
                    )
                ]
            ) from e
        except InvalidTemporalModel as e:
            raise ModelValidationException(
                errors=[self._create_error(message=str(e), specific_path=yaml_path.append("ENERGY_USAGE_MODEL"))]
            ) from e
        except DomainValidationException as e:
            raise ModelValidationException(
                errors=[self._create_error(str(e), specific_path=yaml_path.append("ENERGY_USAGE_MODEL"))]
            ) from e

        if consumes == ConsumptionType.FUEL:
            consumer_fuel = data.fuel
            fuel_yaml_path = yaml_path.append("fuel")
            try:
                fuel = TemporalModel(
                    self._resolve_fuel(
                        consumer_fuel,
                        defaults.fuel,
                    )
                )
            except (
                InvalidReferenceException,
                MissingFuelReference,
                InvalidTemporalModel,
            ) as e:
                raise ModelValidationException(
                    errors=[self._create_error(message=str(e), specific_path=fuel_yaml_path)]
                ) from e

            try:
                return FuelConsumerComponent(
                    id=id,
                    name=data.name,
                    regularity=defaults.regularity,
                    fuel=fuel,
                    energy_usage_model=energy_usage_model,
                    component_type=_get_component_type(data.energy_usage_model),
                    expression_evaluator=self._expression_evaluator,
                )
            except DomainValidationException as e:
                raise ModelValidationException(
                    errors=[self._create_error(message=str(e), specific_path=yaml_path)]
                ) from e
        else:
            try:
                return ElectricityConsumer(
                    id=id,
                    name=data.name,
                    regularity=defaults.regularity,
                    energy_usage_model=energy_usage_model,
                    component_type=_get_component_type(data.energy_usage_model),
                    consumes=consumes,
                    expression_evaluator=self._expression_evaluator,
                )
            except DomainValidationException as e:
                raise ModelValidationException(
                    errors=[self._create_error(message=str(e), specific_path=yaml_path)]
                ) from e

    def map_venting_emitter(
        self,
        data: YamlDirectTypeEmitter | YamlOilTypeEmitter,
        id: uuid.UUID,
        yaml_path: YamlPath,
        defaults: Defaults,
    ) -> DirectVentingEmitter | OilVentingEmitter:
        try:
            if isinstance(data, YamlDirectTypeEmitter):
                emissions = [
                    VentingEmission(
                        name=emission.name,
                        emission_rate=EmissionRate(
                            time_series_expression=TimeSeriesExpression(
                                expression=emission.rate.value,
                                expression_evaluator=self._expression_evaluator,
                                condition=emission.rate.condition,
                            ),
                            unit=emission.rate.unit.to_unit(),
                            rate_type=emission.rate.type,
                            regularity=defaults.regularity,
                        ),
                    )
                    for emission in data.emissions
                ]

                return DirectVentingEmitter(
                    id=id,
                    name=data.name,
                    component_type=data.component_type,
                    emitter_type=data.type,
                    emissions=emissions,
                    regularity=defaults.regularity,
                )
            elif isinstance(data, YamlOilTypeEmitter):
                return OilVentingEmitter(
                    id=id,
                    name=data.name,
                    component_type=data.component_type,
                    emitter_type=data.type,
                    volume=VentingVolume(
                        oil_volume_rate=OilVolumeRate(
                            time_series_expression=TimeSeriesExpression(
                                expression=data.volume.rate.value,
                                expression_evaluator=self._expression_evaluator,
                                condition=data.volume.rate.condition,
                            ),
                            unit=data.volume.rate.unit.to_unit(),
                            rate_type=data.volume.rate.type,
                            regularity=defaults.regularity,
                        ),
                        emissions=[
                            VentingVolumeEmission(name=emission.name, emission_factor=emission.emission_factor)
                            for emission in data.volume.emissions
                        ],
                    ),
                    regularity=defaults.regularity,
                )
            else:
                return assert_never(data)
        except (InvalidExpressionError, DomainValidationException) as e:
            raise ModelValidationException(errors=[self._create_error(message=str(e), specific_path=yaml_path)]) from e

    @overload
    def map_yaml_component(
        self,
        data: YamlInstallation,
        id: uuid.UUID,
        yaml_path: YamlPath,
        parent: uuid.UUID,
        defaults: Defaults = None,
    ) -> InstallationComponent: ...
    @overload
    def map_yaml_component(
        self,
        data: YamlGeneratorSet,
        id: uuid.UUID,
        yaml_path: YamlPath,
        parent: uuid.UUID,
        defaults: Defaults = None,
    ) -> GeneratorSetEnergyComponent: ...
    @overload
    def map_yaml_component(
        self,
        data: YamlElectricityConsumer,
        id: uuid.UUID,
        yaml_path: YamlPath,
        parent: uuid.UUID,
        defaults: Defaults = None,
    ) -> ElectricityConsumer: ...
    @overload
    def map_yaml_component(
        self,
        data: YamlFuelConsumer,
        id: uuid.UUID,
        yaml_path: YamlPath,
        parent: uuid.UUID,
        defaults: Defaults = None,
    ) -> FuelConsumerComponent: ...
    @overload
    def map_yaml_component(
        self,
        data: YamlOilTypeEmitter,
        id: uuid.UUID,
        yaml_path: YamlPath,
        parent: uuid.UUID,
        defaults: Defaults = None,
    ) -> OilVentingEmitter: ...
    @overload
    def map_yaml_component(
        self,
        data: YamlDirectTypeEmitter,
        id: uuid.UUID,
        yaml_path: YamlPath,
        parent: uuid.UUID,
        defaults: Defaults = None,
    ) -> DirectVentingEmitter: ...
    def map_yaml_component(
        self,
        data: YamlInstallation
        | YamlGeneratorSet
        | YamlElectricityConsumer
        | YamlFuelConsumer
        | YamlOilTypeEmitter
        | YamlDirectTypeEmitter,
        id: uuid.UUID,
        yaml_path: YamlPath,
        parent: uuid.UUID,
        defaults: Defaults = None,
    ) -> EnergyComponent:
        self._mapping_context.register_yaml_component(
            yaml_path=yaml_path,
            yaml_component=YamlComponent(
                id=id,
                name=data.name,
                category=data.category,  # type: ignore[arg-type]
            ),
        )
        if not isinstance(data, YamlInstallation):
            # Register regularity if not installation. the installation should not have a regularity itself, but setting regularity for installation sets a default
            self._mapping_context.register_regularity(id, defaults.regularity)

        if isinstance(data, YamlInstallation):
            container = self.map_installation(
                data,
                id=id,
                yaml_path=yaml_path,
                defaults=defaults,
            )
        elif isinstance(data, YamlGeneratorSet):
            assert defaults is not None
            container = self.map_generator_set(
                data,
                id=id,
                yaml_path=yaml_path,
                defaults=defaults,
            )
        elif isinstance(data, YamlElectricityConsumer | YamlFuelConsumer):
            assert defaults is not None
            container = self.map_consumer(
                data,
                id=id,
                yaml_path=yaml_path,
                defaults=defaults,
            )
        elif isinstance(data, YamlDirectTypeEmitter | YamlOilTypeEmitter):
            assert defaults is not None
            container = self.map_venting_emitter(
                data,
                id=id,
                yaml_path=yaml_path,
                defaults=defaults,
            )
        else:
            assert_never(data)

        energy_container_energy_model_builder = self._mapping_context.get_energy_container_energy_model_builder()

        energy_container_energy_model_builder.register_energy_container(
            container_id=id, parent_id=parent, energy_container=container
        )

        return container

    def from_yaml_to_domain(self, model_id: EnergyContainerID, model_name: str) -> Asset:
        installations_path = YamlPath(("installations",))
        try:
            installations = []
            asset_id = uuid.uuid4()
            for installation_index, installation in enumerate(self._configuration.installations):
                installation_yaml_path = installations_path.append(installation_index)
                installation_id = uuid.uuid4()
                parsed_installation = self.map_yaml_component(
                    installation,
                    id=installation_id,
                    yaml_path=installation_yaml_path,
                    parent=asset_id,
                )

                installations.append(parsed_installation)
            ecalc_model = Asset(
                id=model_id,
                name=model_name,
                installations=installations,
            )
            self._mapping_context.get_energy_container_energy_model_builder().register_energy_container(
                asset_id, parent_id=None, energy_container=ecalc_model
            )
            return ecalc_model
        except DomainValidationException as e:
            raise ModelValidationException(
                errors=[
                    ModelValidationError(
                        message=str(e),
                        location=Location(keys=""),
                        file_context=self._configuration.get_file_context(()),
                    )
                ]
            ) from e
