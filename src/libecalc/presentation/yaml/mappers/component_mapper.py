from pydantic import ValidationError

from libecalc.common.component_type import ComponentType
from libecalc.common.consumer_type import ConsumerType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.logger import logger
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.component_validation_error import (
    ComponentValidationException,
    InvalidRegularityException,
    ModelValidationError,
)
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
from libecalc.domain.infrastructure.energy_components.common import Consumer
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.process.dto import ConsumerFunction
from libecalc.domain.regularity import Regularity
from libecalc.dto import FuelType
from libecalc.dto.utils.validators import convert_expression
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException, ReferenceService
from libecalc.presentation.yaml.mappers.consumer_function_mapper import (
    ConsumerFunctionMapper,
)
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
    Location,
)
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import YamlElectricityConsumer
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_fuel_consumer import YamlFuelConsumer
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
    consumer_fuel: str | None | dict,
    default_fuel: str | None,
    references: ReferenceService,
    target_period: Period,
) -> dict[Period, FuelType] | None:
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

    def from_yaml_to_domain(
        self,
        data: YamlFuelConsumer | YamlElectricityConsumer,
        regularity: Regularity,
        consumes: ConsumptionType,
        expression_evaluator: ExpressionEvaluator,
        default_fuel: str | None = None,
    ) -> Consumer:
        component_type = data.component_type
        if component_type not in ["FUEL_CONSUMER", "ELECTRICITY_CONSUMER"]:
            raise DataValidationError(
                data=data.model_dump(),
                message=f"Invalid component type '{component_type}' for component with name '{data.name}'",
            )

        fuel = None
        if consumes == ConsumptionType.FUEL:
            consumer_fuel = data.fuel
            try:
                fuel = _resolve_fuel(consumer_fuel, default_fuel, self.__references, target_period=self._target_period)
            except InvalidReferenceException as e:
                raise DataValidationError(
                    data=data.model_dump(),
                    message=str(e),
                    error_key="fuel",
                ) from e

        try:
            energy_usage_model = self.__energy_usage_model_mapper.from_yaml_to_dto(data.energy_usage_model)
        except ValidationError as e:
            raise DtoValidationError(data=data.model_dump(), validation_error=e) from e

        if consumes == ConsumptionType.FUEL:
            try:
                fuel_consumer_name = data.name
                return FuelConsumer(
                    path_id=PathID(fuel_consumer_name),
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
                    path_id=PathID(electricity_consumer_name),
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
        regularity: Regularity,
        expression_evaluator: ExpressionEvaluator,
        default_fuel: str | None = None,
    ) -> GeneratorSetEnergyComponent:
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
            return GeneratorSetEnergyComponent(
                path_id=PathID(generator_set_name),
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
        data: YamlDirectTypeEmitter | YamlOilTypeEmitter,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
    ) -> DirectVentingEmitter | OilVentingEmitter:
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
                path_id=PathID(data.name),
                expression_evaluator=expression_evaluator,
                component_type=data.component_type,
                user_defined_category=data.category,
                emitter_type=data.type,
                emissions=emissions,
                regularity=regularity,
            )
        elif isinstance(data, YamlOilTypeEmitter):
            return OilVentingEmitter(
                path_id=PathID(data.name),
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
        try:
            regularity = Regularity(
                expression_input=data.regularity,
                target_period=self._target_period,
                expression_evaluator=expression_evaluator,
            )
        except InvalidRegularityException as e:
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        message=e.message,
                        location=Location([data.name]),
                        name=data.name,
                    )
                ]
            ) from e

        hydrocarbon_export = HydrocarbonExport(
            expression_input=data.hydrocarbon_export,
            expression_evaluator=expression_evaluator,
            regularity=regularity,
            target_period=self._target_period,
        )

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

        venting_emitters = [
            self.from_yaml_venting_emitter_to_domain(
                venting_emitter,
                expression_evaluator=expression_evaluator,
                regularity=regularity,
            )
            for venting_emitter in data.venting_emitters or []
        ]

        try:
            return Installation(
                path_id=PathID(data.name),
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
                path_id=PathID(configuration.name),
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
