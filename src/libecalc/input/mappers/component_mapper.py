from datetime import datetime
from typing import Dict, Optional, Union

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.dto.base import ComponentType
from libecalc.dto.types import ConsumerType, ConsumptionType, EnergyModelType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.input.mappers.consumer_function_mapper import ConsumerFunctionMapper
from libecalc.input.mappers.utils import resolve_reference
from libecalc.input.validation_errors import DataValidationError, DtoValidationError
from libecalc.input.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.input.yaml_entities import References
from libecalc.input.yaml_keywords import EcalcYamlKeywords
from libecalc.input.yaml_types.components.system.yaml_compressor_system import (
    YamlCompressorSystem as YamlCompressorSystem,
)
from libecalc.input.yaml_types.components.system.yaml_pump_system import (
    YamlPumpSystem as YamlPumpSystem,
)
from pydantic import ValidationError

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
            none_if_not_found=True,
        )
        if resolved_fuel is None:
            raise ValueError("Fuel not found")

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

        if EcalcYamlKeywords.type in data:
            if data[EcalcYamlKeywords.type] == ComponentType.COMPRESSOR_SYSTEM_V2:
                compressor_system_yaml = YamlCompressorSystem(**data)
                try:
                    return compressor_system_yaml.to_dto(
                        consumes=consumes,
                        regularity=regularity,
                        references=self.__references,
                        target_period=self._target_period,
                        fuel=fuel,
                    )
                except ValidationError as e:
                    raise DtoValidationError(data=data, validation_error=e) from e
            if data[EcalcYamlKeywords.type] == ComponentType.PUMP_SYSTEM_V2:
                pump_system_yaml = YamlPumpSystem(**data)

                try:
                    return pump_system_yaml.to_dto(
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


class EmitterModelMapper:
    """EmitterModel used by DirectEmitters."""

    def __init__(self, references: References, target_period: Period):
        self._target_period = target_period
        self.__references = references

    @staticmethod
    def create_model(model: Dict, regularity: Dict[datetime, Expression]):
        name = model.get(EcalcYamlKeywords.name, "")
        user_defined_category = model.get(EcalcYamlKeywords.user_defined_tag, "")
        emission_rate = model.get(EcalcYamlKeywords.installation_direct_emitter_emission_rate)
        emission_quota = model.get(EcalcYamlKeywords.emission_quota)

        try:
            return dto.EmitterModel(
                name=name,
                user_defined_category=user_defined_category,
                emission_rate=emission_rate,
                emission_quota=emission_quota,
                regularity=regularity,
            )
        except ValidationError as e:
            raise DtoValidationError(data=model, validation_error=e) from e

    def from_yaml_to_dto(
        self, data: Optional[Dict], regularity: Dict[datetime, Expression]
    ) -> Dict[datetime, dto.EmitterModel]:
        time_adjusted_model = define_time_model_for_period(data, target_period=self._target_period)
        return {
            start_date: EmitterModelMapper.create_model(model, regularity=regularity)
            for start_date, model in time_adjusted_model.items()
        }


class DirectEmittersMapper:
    """Mapping DirectEmitters and the corresponding EmitterModel."""

    def __init__(self, references: References, target_period: Period):
        self.__references = references
        self._target_period = target_period
        self.__emitter_model_mapper = EmitterModelMapper(references=references, target_period=target_period)

    def from_yaml_to_dto(
        self,
        data: Dict[str, Dict],
        regularity: Dict[datetime, Expression],
    ) -> dto.DirectEmitter:
        emitter_model = self.__emitter_model_mapper.from_yaml_to_dto(
            data.get(EcalcYamlKeywords.installation_direct_emitter_model),
            regularity=regularity,
        )
        try:
            direct_emitter_name = data.get(EcalcYamlKeywords.name)
            return dto.DirectEmitter(
                name=direct_emitter_name,
                user_defined_category=define_time_model_for_period(
                    data.get(EcalcYamlKeywords.user_defined_tag), target_period=self._target_period
                ),
                emission_name=data.get(EcalcYamlKeywords.installation_direct_emitter_emission_name),
                emitter_model=emitter_model,
                regularity=regularity,
            )
        except ValidationError as e:
            raise DtoValidationError(data=data, validation_error=e) from e


class InstallationMapper:
    def __init__(self, references: References, target_period: Period):
        self.__references = references
        self._target_period = target_period
        self.__generator_set_mapper = GeneratorSetMapper(references=references, target_period=target_period)
        self.__consumer_mapper = ConsumerMapper(references=references, target_period=target_period)
        self.__direct_emitters_mapper = DirectEmittersMapper(references=references, target_period=target_period)

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
        direct_emitters = [
            self.__direct_emitters_mapper.from_yaml_to_dto(
                direct_emitters,
                regularity=regularity,
            )
            for direct_emitters in data.get(EcalcYamlKeywords.installation_direct_emitters, [])
        ]

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
                direct_emitters=direct_emitters,
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
