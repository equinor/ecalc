from abc import ABC, abstractmethod
from uuid import UUID

from libecalc.common.time_utils import Period
from libecalc.presentation.yaml.domain.ecalc_component import (
    EcalcComponent,
    EvalInputType,
    ModelType,
    RegisteredComponent,
)


class ProcessService(ABC):
    @abstractmethod
    def register_component(
        self,
        ecalc_component: EcalcComponent,
        model: ModelType,
        evaluation_input: EvalInputType | None = None,
        consumer_system_id: UUID | None = None,
    ): ...

    @abstractmethod
    def get_compressor_process_systems(self) -> dict[UUID, RegisteredComponent]: ...

    @abstractmethod
    def get_pump_process_systems(self) -> dict[UUID, RegisteredComponent]: ...

    @abstractmethod
    def get_compressors_sampled(self) -> dict[UUID, RegisteredComponent]: ...

    @abstractmethod
    def map_model_to_consumer(self, consumer_id: UUID, period: Period, component_ids: list[UUID]): ...

    @abstractmethod
    def get_components_for_consumer(self, consumer_id: UUID, period: Period) -> list[RegisteredComponent]: ...
