from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import (
    ConsumerSystemConsumerFunction,
    PumpSystemConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    PumpSystemOperationalSettingExpressions,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.types import ConsumerSystemComponent
from libecalc.domain.process.dto.consumer_system import (
    PumpSystemConsumerFunction as PumpSystemConsumerFunctionDTO,
)
from libecalc.domain.process.dto.consumer_system import (
    PumpSystemOperationalSetting,
)
from libecalc.domain.process.pump.factory import create_pump_model
from libecalc.expression import Expression

from .compressor_system_consumer_function import (
    map_discharge_pressures,
    map_rates,
    map_suction_pressures,
)


def _map_operational_setting(
    operational_setting: PumpSystemOperationalSetting,
    system_rate: Expression | None,
    system_fluid_density: Expression | None,
    number_of_pumps: int,
) -> PumpSystemOperationalSettingExpressions:
    fluid_densities = None
    if operational_setting.fluid_densities is not None:
        fluid_densities = operational_setting.fluid_densities
    elif system_fluid_density is not None:
        fluid_densities = [system_fluid_density] * number_of_pumps

    return PumpSystemOperationalSettingExpressions(
        fluid_densities=fluid_densities,
        discharge_pressures=map_discharge_pressures(
            operational_setting=operational_setting, number_of_consumers=number_of_pumps
        ),
        suction_pressures=map_suction_pressures(
            operational_setting=operational_setting, number_of_consumers=number_of_pumps
        ),
        cross_overs=operational_setting.crossover,
        rates=map_rates(
            operational_setting=operational_setting, system_rate=system_rate, number_of_consumers=number_of_pumps
        ),
    )


def create_pump_system(model_dto: PumpSystemConsumerFunctionDTO) -> ConsumerSystemConsumerFunction:
    return PumpSystemConsumerFunction(
        consumer_components=[
            ConsumerSystemComponent(
                name=pump.name,
                facility_model=create_pump_model(pump_model_dto=pump.pump_model),
            )
            for pump in model_dto.pumps
        ],
        operational_settings_expressions=[
            _map_operational_setting(
                operational_setting,
                system_rate=model_dto.total_system_rate,
                system_fluid_density=model_dto.fluid_density,
                number_of_pumps=len(model_dto.pumps),
            )
            for operational_setting in model_dto.operational_settings
        ],
        condition_expression=model_dto.condition,
        power_loss_factor_expression=model_dto.power_loss_factor,
    )
