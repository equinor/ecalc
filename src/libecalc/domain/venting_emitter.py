from libecalc.common.utils.rates import RateType, TimeSeriesStreamDayRate
from libecalc.dto.base import ComponentType, ConsumerUserDefinedCategoryType


class Rate:
    def __init__(self, value: TimeSeriesStreamDayRate, rate_type: RateType):
        self.value = value
        self.type = rate_type


class Emission:
    def __init__(self, name: str, rate: Rate):
        self.name = name
        self.rate = rate


class VentingEmitter:
    def __init__(
        self,
        name: str,
        category: ConsumerUserDefinedCategoryType,
        emission: Emission,
        emitter_id: str,
        component_type: ComponentType,
    ):
        self.name = name
        self.user_defined_category = category
        self.emission = emission
        self.id = emitter_id
        self.component_type = component_type

    def storage_volume(self, volume_emission_factor: float):
        raise NotImplementedError

    def loading_volume(self, volume_emission_factor: float):
        raise NotImplementedError
