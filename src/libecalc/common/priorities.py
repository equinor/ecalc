from typing import Dict, TypeVar

TPriorityValue = TypeVar("TPriorityValue")

PriorityID = str

Priorities = Dict[PriorityID, TPriorityValue]
