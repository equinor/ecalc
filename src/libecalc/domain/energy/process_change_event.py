from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ProcessChangedEvent:
    """
    An event representing a change in the process system
    """

    start: datetime
    name: str
    description: str | None = None
