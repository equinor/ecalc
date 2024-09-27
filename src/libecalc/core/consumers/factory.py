from typing import Union, overload

from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Period
from libecalc.core.consumers.compressor import Compressor
from libecalc.core.consumers.pump import Pump
from libecalc.core.models.compressor import create_compressor_model
from libecalc.core.models.pump import create_pump_model
from libecalc.dto.components import CompressorComponent, PumpComponent


@overload
def create_consumer(consumer: CompressorComponent, period: Period) -> Compressor: ...


@overload
def create_consumer(consumer: PumpComponent, period: Period) -> Pump:  # type: ignore[misc]
    ...


def create_consumer(
    consumer: Union[CompressorComponent, PumpComponent],
    period: Period,
) -> Union[Compressor, Pump]:
    periods = consumer.energy_usage_model.keys()
    energy_usage_models = list(consumer.energy_usage_model.values())

    model_for_period = None
    for _period, energy_usage_model in zip(periods, energy_usage_models):
        if period in _period:
            model_for_period = energy_usage_model

    if model_for_period is None:
        raise ValueError(f"Could not find model for consumer {consumer.name} at timestep {period}")

    if consumer.component_type == ComponentType.COMPRESSOR:
        return Compressor(
            id=consumer.id,
            compressor_model=create_compressor_model(
                compressor_model_dto=model_for_period,
            ),
        )
    elif consumer.component_type == ComponentType.PUMP:
        return Pump(
            id=consumer.id,
            pump_model=create_pump_model(
                pump_model_dto=model_for_period,
            ),
        )
    else:
        raise TypeError(f"Unknown consumer. Received consumer with type '{consumer.component_type}'")
