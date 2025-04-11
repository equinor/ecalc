from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import (
    CompressorSystemConsumerFunction,
    ConsumerSystemConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    CompressorSystemOperationalSettingExpressions,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.types import ConsumerSystemComponent
from libecalc.domain.process.compressor.core import create_compressor_model
from libecalc.domain.process.dto.consumer_system import (
    CompressorSystemConsumerFunction as CompressorSystemConsumerFunctionDTO,
)
from libecalc.domain.process.dto.consumer_system import CompressorSystemOperationalSetting, SystemOperationalSetting
from libecalc.expression import Expression


def _map_operational_settings(
    operational_settings: CompressorSystemOperationalSetting,
    system_rate: Expression | None,
    number_of_compressors: int,
) -> CompressorSystemOperationalSettingExpressions:
    return CompressorSystemOperationalSettingExpressions(
        rates=map_rates(
            operational_setting=operational_settings, system_rate=system_rate, number_of_consumers=number_of_compressors
        ),
        discharge_pressures=map_discharge_pressures(
            operational_setting=operational_settings, number_of_consumers=number_of_compressors
        ),
        suction_pressures=map_suction_pressures(
            operational_setting=operational_settings, number_of_consumers=number_of_compressors
        ),
        cross_overs=operational_settings.crossover,
    )


def create_compressor_system(model_dto: CompressorSystemConsumerFunctionDTO) -> ConsumerSystemConsumerFunction:
    compressors = [
        ConsumerSystemComponent(
            name=compressor.name,
            facility_model=create_compressor_model(compressor_model_dto=compressor.compressor_train),
        )
        for compressor in model_dto.compressors
    ]

    operational_settings = [
        _map_operational_settings(
            operational_settings=operational_setting,
            number_of_compressors=len(model_dto.compressors),
            system_rate=model_dto.total_system_rate,
        )
        for operational_setting in model_dto.operational_settings
    ]
    return CompressorSystemConsumerFunction(
        consumer_components=compressors,
        operational_settings_expressions=operational_settings,
        condition_expression=model_dto.condition,
        power_loss_factor_expression=model_dto.power_loss_factor,
    )


def map_discharge_pressures(
    operational_setting: SystemOperationalSetting,
    number_of_consumers: int,
) -> list[Expression]:
    if operational_setting.discharge_pressure is not None:
        return [operational_setting.discharge_pressure] * number_of_consumers
    elif operational_setting.discharge_pressures is not None:
        return operational_setting.discharge_pressures
    else:
        # If not specified, default to zero-expression.
        return [Expression.setup_from_expression(0)] * number_of_consumers


def map_suction_pressures(operational_setting: SystemOperationalSetting, number_of_consumers: int) -> list[Expression]:
    if operational_setting.suction_pressure is not None:
        return [operational_setting.suction_pressure] * number_of_consumers
    elif operational_setting.suction_pressures is not None:
        return operational_setting.suction_pressures
    else:
        # If not specified, default to zero-expression.
        return [Expression.setup_from_expression(0)] * number_of_consumers


def map_rates(
    operational_setting: SystemOperationalSetting,
    system_rate: Expression | None,
    number_of_consumers: int,
) -> list[Expression]:
    if operational_setting.rates is not None:
        return operational_setting.rates
    elif operational_setting.rate_fractions:
        # Multiply rate_fractions with total system rate to get rates
        return [
            Expression.multiply(
                system_rate,
                rate_fraction,
            )
            for rate_fraction in operational_setting.rate_fractions
        ]
    else:
        # If not specified, default to zero-expression.
        return [Expression.setup_from_expression(0)] * number_of_consumers
