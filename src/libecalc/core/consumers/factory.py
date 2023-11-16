from datetime import datetime
from typing import Union, overload

from libecalc import dto
from libecalc.common.time_utils import Periods
from libecalc.core.consumers.compressor import Compressor
from libecalc.core.consumers.pump import Pump
from libecalc.core.models.compressor import create_compressor_model
from libecalc.core.models.pump import create_pump_model
from libecalc.dto.base import ComponentType


@overload
def create_consumer(consumer: dto.components.CompressorComponent, timestep: datetime) -> Compressor:
    ...


@overload
def create_consumer(consumer: dto.components.PumpComponent, timestep: datetime) -> Pump:  # type: ignore[misc]
    ...


def create_consumer(
    consumer: Union[dto.components.CompressorComponent, dto.components.PumpComponent],
    timestep: datetime,
) -> Union[Compressor, Pump]:
    periods = Periods.create_periods(list(consumer.energy_usage_model.keys()), include_before=False)
    energy_usage_models = list(consumer.energy_usage_model.values())

    model_for_timestep = None
    for period, energy_usage_model in zip(periods, energy_usage_models):
        if timestep in period:
            model_for_timestep = energy_usage_model

    if model_for_timestep is None:
        raise ValueError(f"Could not find model for consumer {consumer.name} at timestep {timestep}")

    if consumer.component_type == ComponentType.COMPRESSOR:
        return Compressor(
            id=consumer.id,
            compressor_model=create_compressor_model(
                compressor_model_dto=model_for_timestep,
            ),
        )
    elif consumer.component_type == ComponentType.PUMP:
        return Pump(
            id=consumer.id,
            pump_model=create_pump_model(
                pump_model_dto=model_for_timestep,
            ),
        )
    else:
        raise TypeError(f"Unknown consumer. Received consumer with type '{consumer.component_type}'")
