from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class YamlComponent:
    id: UUID
    name: str
    category: str | dict[datetime, str] | None
