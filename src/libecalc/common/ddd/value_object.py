from __future__ import annotations

from dataclasses import dataclass
from typing import dataclass_transform

"""
Base class for DDD Value Objects.

Value Objects are defined by their attributes, not by an identity.
Properties enforced by this base class:

- Immutable: fields cannot be reassigned after creation (frozen_default=True)
- Equality by value: two instances with identical field values are equal. (eq_default=True).
    Will generate __eq__ and __hash__ based on values
- Hashable: can be used in sets and as dict keys, since they are immutable.
- Slots: Since value objects are frozen/immutable, we can safely use __slots__ to save memory

Ex:

@value_object
class MyValueObject:
    ...

Instead of using @dataclass
"""


@dataclass_transform(frozen_default=True, eq_default=True)
def value_object[T](cls: type[T]) -> type[T]:
    """
    Basically 1. Telling typechecker which guarantees this decorator gives and 2. Construct the class that
    does exactly that.


    Args:
        cls:

    Returns:

    """
    return dataclass(cls, frozen=True, eq=True, slots=True)
