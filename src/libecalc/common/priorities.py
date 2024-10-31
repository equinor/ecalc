from typing import TypeVar

TPriorityValue = TypeVar("TPriorityValue")

PriorityID = str

Priorities = dict[PriorityID, TPriorityValue]
