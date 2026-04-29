from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, is_dataclass
from typing import Any, dataclass_transform


@dataclass_transform(frozen_default=True, eq_default=True, slots_default=True)
class ValueObject(ABC):  # noqa: B024 I want to explicitly signal to not instantiate this class directly
    """
    Base class for DDD Value Objects.

    Value Objects are defined by their attributes, not by an identity.
    Properties enforced by this base class:

    - Immutable: fields cannot be reassigned after creation (frozen_default=True)
    - Equality by value: two instances with identical field values are equal. (eq_default=True).
        Will generate __eq__ and __hash__ based on values
    - Hashable: can be used in sets and as dict keys, since they are immutable.

    Ex:

    class MyValueObject(ValueObject):
        ...

    Currently no other requirements
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        if not is_dataclass(cls):
            dataclass(cls, frozen=True, eq=True, slots=True)
