from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.pump_consumer_function import (
    PumpConsumerFunction,
)
from libecalc.domain.process.pump.factory import create_pump_model
from libecalc.domain.process.pump.pump_consumer_function import PumpConsumerFunction as PumpConsumerFunctionDTO


def create_pump_consumer_function(model_dto: PumpConsumerFunctionDTO) -> PumpConsumerFunction:
    pump_model = create_pump_model(pump_model_dto=model_dto.model)
    return PumpConsumerFunction(
        condition_expression=model_dto.condition,  # type: ignore[arg-type]
        power_loss_factor_expression=model_dto.power_loss_factor,  # type: ignore[arg-type]
        pump_function=pump_model,
        rate_expression=model_dto.rate_standard_m3_day,  # type: ignore[arg-type]
        suction_pressure_expression=model_dto.suction_pressure,  # type: ignore[arg-type]
        discharge_pressure_expression=model_dto.discharge_pressure,  # type: ignore[arg-type]
        fluid_density_expression=model_dto.fluid_density,  # type: ignore[arg-type]
    )
