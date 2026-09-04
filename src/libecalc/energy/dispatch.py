import abc
from collections.abc import Sequence

from libecalc.common.ddd import value_object
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import InvalidDispatchError


@value_object
class ProviderAvailability:
    provider_id: EnergyUnitId
    available: Energy | None  # None means unlimited.


class DispatchStrategy(abc.ABC):
    """How a junction splits its demand across the providers feeding it."""

    @abc.abstractmethod
    def get_provider_ids(self) -> frozenset[EnergyUnitId]: ...

    @abc.abstractmethod
    def allocate(
        self,
        demand: Energy,
        candidates: Sequence[ProviderAvailability],
    ) -> dict[EnergyUnitId, Energy]:
        """Split demand across candidates. Include zero energy providers and preserve the total demand."""
        ...


@value_object
class PriorityDispatch(DispatchStrategy):
    """Fill providers in order up to availability; the last provider absorbs any remainder."""

    order: tuple[EnergyUnitId, ...]

    def get_provider_ids(self) -> frozenset[EnergyUnitId]:
        return frozenset(self.order)

    def allocate(
        self,
        demand: Energy,
        candidates: Sequence[ProviderAvailability],
    ) -> dict[EnergyUnitId, Energy]:
        availability_by_provider = {candidate.provider_id: candidate.available for candidate in candidates}

        if not self.order:
            raise InvalidDispatchError("Priority dispatch requires at least one provider in its order")

        missing_providers = [provider_id for provider_id in self.order if provider_id not in availability_by_provider]
        if missing_providers:
            raise InvalidDispatchError(
                f"Priority dispatch order references providers missing from the candidates: {missing_providers}"
            )

        nothing = type(demand)(value=0)
        allocations: dict[EnergyUnitId, Energy] = {candidate.provider_id: nothing for candidate in candidates}
        remaining = demand

        for provider_id in self.order:
            available = availability_by_provider[provider_id]
            allocated = remaining if available is None else min(remaining, available)
            allocations[provider_id] = allocated
            remaining -= allocated

        if remaining > nothing:
            allocations[self.order[-1]] += remaining

        return allocations
