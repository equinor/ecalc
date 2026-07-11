"""Parameter handles — the only reference type in v3.

``Param(owner, field)`` names one settable input on a unit, shaft or
recirculation loop. References are object handles, not strings: an invalid
reference is impossible to construct (the field is validated with ``hasattr``),
so there is no separate compilation/validation pass and no name registry.

A ``Param`` hashes and compares by ``(id(owner), field)`` so it works as a dict
key regardless of whether the owner defines value equality. The solver's answer
is a ``{Param: float}`` map; stale state is unrepresentable because evaluation
reads overrides through these handles and never mutates the owners.
"""

from __future__ import annotations

from dataclasses import dataclass


class Unset:
    """Singleton sentinel for an input the solver must supply (e.g. shaft speed)."""

    _instance: Unset | None = None

    def __new__(cls) -> Unset:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"


UNSET = Unset()


@dataclass(frozen=True, eq=False)
class Param:
    """A handle to one settable field on a unit, shaft or recirculation loop."""

    owner: object
    field: str

    def __post_init__(self) -> None:
        if not hasattr(self.owner, self.field):
            raise ValueError(
                f"{type(self.owner).__name__} has no field '{self.field}'; cannot create a Param referencing it."
            )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Param) and other.owner is self.owner and other.field == self.field

    def __hash__(self) -> int:
        return hash((id(self.owner), self.field))

    def __repr__(self) -> str:
        return f"Param({type(self.owner).__name__}, {self.field!r})"
