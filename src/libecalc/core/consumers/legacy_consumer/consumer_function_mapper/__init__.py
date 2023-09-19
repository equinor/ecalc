from typing import Any, Callable, Dict, Union

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.core.consumers.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.dto.types import ConsumerType

from .compressor_consumer_function import create_compressor_consumer_function
from .compressor_system_consumer_function import create_compressor_system
from .direct_consumer_function import create_direct_consumer_function
from .pump_consumer_function import create_pump_consumer_function
from .pump_system_consumer_function import create_pump_system
from .tabulated import create_tabulated_consumer_function

TConsumerFunction = Union[
    dto.DirectConsumerFunction,
    dto.CompressorConsumerFunction,
    dto.CompressorSystemConsumerFunction,
    dto.TabulatedConsumerFunction,
    dto.PumpConsumerFunction,
]

consumer_function_map: Dict[ConsumerType, Callable[[TConsumerFunction], ConsumerFunction]] = {
    ConsumerType.DIRECT: create_direct_consumer_function,
    ConsumerType.PUMP_SYSTEM: create_pump_system,
    ConsumerType.COMPRESSOR_SYSTEM: create_compressor_system,
    ConsumerType.COMPRESSOR: create_compressor_consumer_function,
    ConsumerType.TABULATED: create_tabulated_consumer_function,
    ConsumerType.PUMP: create_pump_consumer_function,
}


def _invalid_energy_usage_type(energy_usage_model: Any):
    try:
        msg = f"Unsupported consumer function type: {energy_usage_model.typ}."
        logger.error(msg)
        raise TypeError(msg)
    except AttributeError as e:
        msg = "Unsupported consumer function type."
        logger.exception(msg)
        raise TypeError(msg) from e


class EnergyModelMapper:
    @staticmethod
    def from_dto_to_domain(energy_usage_model: TConsumerFunction) -> ConsumerFunction:
        return consumer_function_map.get(energy_usage_model.typ, _invalid_energy_usage_type)(energy_usage_model)
