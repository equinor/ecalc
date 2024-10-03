from typing import Union, assert_never, overload

from libecalc.presentation.yaml.domain.components.consumers.compressor import Compressor
from libecalc.presentation.yaml.domain.components.consumers.pump import Pump
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.yaml_types.components.yaml_compressor import YamlCompressor
from libecalc.presentation.yaml.yaml_types.components.yaml_pump import YamlPump


@overload
def create_consumer(
    consumer: YamlCompressor,
    reference_service: ReferenceService,
) -> Compressor: ...


@overload
def create_consumer(
    consumer: YamlPump,
    reference_service: ReferenceService,
) -> Pump: ...


def create_consumer(
    consumer: Union[YamlCompressor, YamlPump],
    reference_service: ReferenceService,
) -> Union[Compressor, Pump]:
    if isinstance(consumer, YamlCompressor):
        return Compressor(
            yaml_compressor=consumer,
            reference_service=reference_service,
        )
    elif isinstance(consumer, YamlPump):
        return Pump(
            yaml_pump=consumer,
            reference_service=reference_service,
        )
    else:
        assert_never(consumer)
