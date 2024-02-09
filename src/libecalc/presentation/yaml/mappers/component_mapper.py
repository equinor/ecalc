from datetime import datetime
from typing import Dict, Optional, Union

from pydantic import ValidationError

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.dto.base import ComponentType
from libecalc.dto.types import ConsumerType, ConsumptionType, EnergyModelType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.consumer_function_mapper import (
    ConsumerFunctionMapper,
)
from libecalc.presentation.yaml.mappers.utils import resolve_reference
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
)
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.components.system.yaml_consumer_system import (
    YamlConsumerSystem,
)
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
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


def _get_component_type(energy_usage_models: Dict[datetime, dto.ConsumerFunction]) -> ComponentType:
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
    consumer_fuel: Union[Optional[str], Dict],
    default_fuel: Optional[str],
    references: References,
    target_period: Period,
) -> Optional[Dict[datetime, dto.types.FuelType]]:
    fuel = consumer_fuel or default_fuel  # Use parent fuel only if not specified on this consumer

    if fuel is None:
        return None

    time_adjusted_fuel = define_time_model_for_period(fuel, target_period=target_period)

    temporal_fuel_model = {}
    for start_time, fuel in time_adjusted_fuel.items():
        resolved_fuel = resolve_reference(
            fuel,
            references=references.fuel_types,
        )

        temporal_fuel_model[start_time] = resolved_fuel

    return temporal_fuel_model


class ConsumerMapper:
    def __init__(self, references: References, target_period: Period):
        self.__references = references
        self._target_period = target_period
        self.__energy_usage_model_mapper = ConsumerFunctionMapper(references=references, target_period=target_period)

    def from_yaml_to_dto(
        self,
        data: Dict,
        regularity: Dict[datetime, Expression],
        consumes: ConsumptionType,
        default_fuel: Optional[str] = None,
    ) -> dto.components.Consumer:
        component_type = data.get(EcalcYamlKeywords.type)
        if component_type is not None and component_type != ComponentType.CONSUMER_SYSTEM_V2:
            # We have type here for v2, check that type is valid
            raise DataValidationError(
                data=data,
                message=f"Invalid component type '{component_type}' for component with name '{data.get(EcalcYamlKeywords.name)}'",
            )

        fuel = None
        if consumes == ConsumptionType.FUEL:
            try:
                fuel = _resolve_fuel(
                    data.get(EcalcYamlKeywords.fuel), default_fuel, self.__references, target_period=self._target_period
                )
            except ValueError as e:
                raise DataValidationError(
                    data=data,
                    message=f"Fuel '{data.get(EcalcYamlKeywords.fuel)}' does not exist",
                    error_key="fuel",
                ) from e

        if component_type is not None:
            if component_type == ComponentType.CONSUMER_SYSTEM_V2:
                try:
                    compressor_system_yaml = YamlConsumerSystem(**data)
                    return compressor_system_yaml.to_dto(
                        consumes=consumes,
                        regularity=regularity,
                        references=self.__references,
                        target_period=self._target_period,
                        fuel=fuel,
                    )
                except ValidationError as e:
                    raise DtoValidationError(data=data, validation_error=e) from e

        energy_usage_model = resolve_reference(
            data.get(EcalcYamlKeywords.energy_usage_model),
            references=self.__references.models,
        )

        try:
            energy_usage_model = self.__energy_usage_model_mapper.from_yaml_to_dto(energy_usage_model)
        except ValidationError as e:
            raise DtoValidationError(data=data, validation_error=e) from e

        if consumes == ConsumptionType.FUEL:
            try:
                fuel_consumer_name = data.get(EcalcYamlKeywords.name)
                return dto.FuelConsumer(
                    name=fuel_consumer_name,
                    user_defined_category=define_time_model_for_period(
                        data.get(EcalcYamlKeywords.user_defined_tag), target_period=self._target_period
                    ),
                    regularity=regularity,
                    fuel=fuel,
                    energy_usage_model=energy_usage_model,
                    component_type=_get_component_type(energy_usage_model),
                )
            except ValidationError as e:
                raise DtoValidationError(data=data, validation_error=e) from e
        else:
            try:
                electricity_consumer_name = data.get(EcalcYamlKeywords.name)
                return dto.ElectricityConsumer(
                    name=electricity_consumer_name,
                    regularity=regularity,
                    user_defined_category=define_time_model_for_period(
                        data.get(EcalcYamlKeywords.user_defined_tag), target_period=self._target_period
                    ),
                    energy_usage_model=energy_usage_model,
                    component_type=_get_component_type(energy_usage_model),
                )
            except ValidationError as e:
                raise DtoValidationError(data=data, validation_error=e) from e


class GeneratorSetMapper:
    def __init__(self, references: References, target_period: Period):
        self.__references = references
        self._target_period = target_period
        self.__consumer_mapper = ConsumerMapper(references=references, target_period=target_period)

    def from_yaml_to_dto(
        self,
        data: Dict,
        regularity: Dict[datetime, Expression],
        default_fuel: Optional[str] = None,
    ) -> dto.GeneratorSet:
        try:
            fuel = _resolve_fuel(
                data.get(EcalcYamlKeywords.fuel), default_fuel, self.__references, target_period=self._target_period
            )
        except ValueError as e:
            raise DataValidationError(
                data=data,
                message=f"Fuel '{data.get(EcalcYamlKeywords.fuel)}' does not exist",
                error_key="fuel",
            ) from e
        generator_set_model_data = define_time_model_for_period(
            data.get(EcalcYamlKeywords.el2fuel), target_period=self._target_period
        )
        generator_set_model = {
            start_time: resolve_reference(
                model_timestep,
                references=self.__references.models,
            )
            for start_time, model_timestep in generator_set_model_data.items()
        }

        # When consumers was created directly in the return dto.GeneratorSet - function,
        # the error message indicated some problems in the creation of consumers, but was due to a validation error for
        # the generator sets electricity to fuel input. Thus, create/parse things one by one to ensure reliable errors
        consumers = [
            self.__consumer_mapper.from_yaml_to_dto(
                consumer,
                regularity=regularity,
                consumes=ConsumptionType.ELECTRICITY,
            )
            for consumer in data.get(EcalcYamlKeywords.consumers, [])
        ]
        try:
            generator_set_name = data.get(EcalcYamlKeywords.name)
            return dto.GeneratorSet(
                name=generator_set_name,
                fuel=fuel,
                regularity=regularity,
                generator_set_model=generator_set_model,
                consumers=consumers,
                user_defined_category=define_time_model_for_period(
                    data.get(EcalcYamlKeywords.user_defined_tag), target_period=self._target_period
                ),
            )
        except ValidationError as e:
            raise DtoValidationError(data=data, validation_error=e) from e


class InstallationMapper:
    def __init__(self, references: References, target_period: Period):
        self.__references = references
        self._target_period = target_period
        self.__generator_set_mapper = GeneratorSetMapper(references=references, target_period=target_period)
        self.__consumer_mapper = ConsumerMapper(references=references, target_period=target_period)

    def from_yaml_to_dto(self, data: Dict) -> dto.Installation:
        fuel_data = data.get(EcalcYamlKeywords.fuel)
        regularity = define_time_model_for_period(
            convert_expression(data.get(EcalcYamlKeywords.regularity, 1)), target_period=self._target_period
        )

        installation_name = data.get(EcalcYamlKeywords.name)

        generator_sets = [
            self.__generator_set_mapper.from_yaml_to_dto(
                generator_set,
                regularity=regularity,
                default_fuel=fuel_data,
            )
            for generator_set in data.get(EcalcYamlKeywords.generator_sets, [])
        ]
        fuel_consumers = [
            self.__consumer_mapper.from_yaml_to_dto(
                fuel_consumer,
                regularity=regularity,
                consumes=ConsumptionType.FUEL,
                default_fuel=fuel_data,
            )
            for fuel_consumer in data.get(EcalcYamlKeywords.fuel_consumers, [])
        ]

        venting_emitters = []
        for venting_emitter in data.get(EcalcYamlKeywords.installation_venting_emitters, []):
            try:
                venting_emitters.append(YamlVentingEmitter(**venting_emitter))
            except ValidationError as e:
                raise DtoValidationError(data=venting_emitter, validation_error=e) from e

        hydrocarbon_export = define_time_model_for_period(
            data.get(
                EcalcYamlKeywords.hydrocarbon_export,
                Expression.setup_from_expression(0),
            ),
            target_period=self._target_period,
        )

        try:
            return dto.Installation(
                name=installation_name,
                regularity=regularity,
                hydrocarbon_export=hydrocarbon_export,
                fuel_consumers=[*generator_sets, *fuel_consumers],
                venting_emitters=venting_emitters,
                user_defined_category=data.get(EcalcYamlKeywords.user_defined_tag),
            )
        except ValidationError as e:
            raise DtoValidationError(data=data, validation_error=e) from e


class EcalcModelMapper:
    def __init__(
        self,
        references: References,
        target_period: Period,
    ):
        self.__references = references
        self.__installation_mapper = InstallationMapper(references=references, target_period=target_period)

    def from_yaml_to_dto(self, configuration: PyYamlYamlModel, name: str) -> dto.Asset:
        try:
            ecalc_model = dto.Asset(
                name=name,
                installations=[
                    self.__installation_mapper.from_yaml_to_dto(installation)
                    for installation in configuration.installations
                ],
            )
            return ecalc_model
        except ValidationError as e:
            raise DtoValidationError(data=None, validation_error=e) from e
