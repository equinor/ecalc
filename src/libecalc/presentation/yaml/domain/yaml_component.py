from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from libecalc.dto.types import ConsumerUserDefinedCategoryType


@dataclass
class YamlComponent:
    id: UUID
    name: str
    category: (
        str | dict[datetime, str] | ConsumerUserDefinedCategoryType | dict[datetime, ConsumerUserDefinedCategoryType]
    )
