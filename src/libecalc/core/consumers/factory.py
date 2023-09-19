from typing import Union, overload

from libecalc import dto
from libecalc.core.consumers.compressor import Compressor
from libecalc.core.consumers.pump import Pump
from libecalc.dto.base import ComponentType


@overload
def create_consumer(consumer: dto.components.CompressorComponent) -> Compressor:
    ...


@overload
def create_consumer(consumer: dto.components.PumpComponent) -> Pump:  # type: ignore[misc]
    ...


def create_consumer(
    consumer: Union[dto.components.CompressorComponent, dto.components.PumpComponent],
) -> Union[Compressor, Pump]:
    if consumer.component_type == ComponentType.COMPRESSOR:
        return Compressor(id=consumer.id, energy_usage_model=consumer.energy_usage_model)
    elif consumer.component_type == ComponentType.PUMP:
        return Pump(id=consumer.id, energy_usage_model=consumer.energy_usage_model)
    else:
        raise TypeError(f"Unknown consumer. Received consumer with type '{consumer.component_type}'")
