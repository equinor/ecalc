from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Protocol, TypeVar

from libecalc.common.temporal_model import TemporalModel

# from libecalc.core.result import EcalcModelResult # TODO: Cannot include due to circular import ...yet
from libecalc.domain.stream_conditions import StreamConditions
from libecalc.dto.base import ComponentType, ConsumerUserDefinedCategoryType


class Evaluationable(Protocol):
    def evaluate(self, streams: List[StreamConditions]) -> Any:
        ...


EquipmentType = TypeVar("EquipmentType", bound=Evaluationable)


@dataclass
class TemporalEquipment(Generic[EquipmentType]):
    """
    The temporal layer of equipment, includes metadata and the equipment domain model itself for each timestep, basically
    a parsed and flattened version of the yaml

    Except from data, the properties are just needed for metadata, aggregation etc for LTP and similar

    This class should be the same for all equipment represented in e.g. yaml, basically a wrapper around the core domain layer
    """

    id: Optional[str]
    component_type: Optional[ComponentType]
    name: Optional[str]
    user_defined_category: Optional[Dict[datetime, ConsumerUserDefinedCategoryType]]
    fuel: Optional[Dict[datetime, Any]]  # cannot specify FuelType due to circular import ..
    data: TemporalModel[EquipmentType]

    def evaluate(self, stream_conditions: Dict[datetime, List[StreamConditions]]) -> Any:
        """
        Evaluate the temporal domain models.

        TODO: Here we might want to use cache somehow, either for this single run wrt same results for same timesteps,
        but also across runs etc

        Args:
            stream_conditions:

        Returns:

        """
        if not stream_conditions:
            raise ValueError(f"Missing stream conditions for {self.name}")

        result = None
        for timestep, model in self.data.items():
            if result is None:  # TODO: Use map reduce
                result = model.evaluate(stream_conditions.get(timestep.start))
            else:
                result.extend(model.evaluate(stream_conditions.get(timestep.start)))

        return result
