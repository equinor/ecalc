import abc
from collections.abc import Sequence

from libecalc.common.ddd import value_object
from libecalc.energy.energy_types import Energy
from libecalc.energy.errors import InvalidDispatchError


@value_object
class Candidate[T_id]:
    candidate_id: T_id
    available: Energy | None  # None means unlimited.


class DispatchStrategy[T_id](abc.ABC):
    """How a junction splits its demand across the candidates feeding it."""

    @abc.abstractmethod
    def get_candidate_ids(self) -> frozenset[T_id]: ...

    @abc.abstractmethod
    def allocate(
        self,
        demand: Energy,
        candidates: Sequence[Candidate[T_id]],
    ) -> dict[T_id, Energy]:
        """Split demand across candidates. Include zero energy candidates and preserve the total demand."""
        ...


@value_object
class PriorityDispatch[T_id](DispatchStrategy[T_id]):
    """Fill candidates in order up to availability; the last candidate absorbs any remainder."""

    order: tuple[T_id, ...]

    def get_candidate_ids(self) -> frozenset[T_id]:
        return frozenset(self.order)

    def allocate(
        self,
        demand: Energy,
        candidates: Sequence[Candidate[T_id]],
    ) -> dict[T_id, Energy]:
        availability_by_candidate = {candidate.candidate_id: candidate.available for candidate in candidates}

        if not self.order:
            raise InvalidDispatchError("Priority dispatch requires at least one candidate in its order")

        missing_candidates = [
            candidate_id for candidate_id in self.order if candidate_id not in availability_by_candidate
        ]
        if missing_candidates:
            raise InvalidDispatchError(
                f"Priority dispatch order references candidates missing from the allocation input: {missing_candidates}"
            )

        nothing = type(demand)(value=0)
        allocations: dict[T_id, Energy] = {candidate.candidate_id: nothing for candidate in candidates}
        remaining = demand

        for candidate_id in self.order:
            available = availability_by_candidate[candidate_id]
            allocated = remaining if available is None else min(remaining, available)
            allocations[candidate_id] = allocated
            remaining -= allocated

        # Remaining demand given to the last candidate (capacity exceeded)
        if remaining > nothing:
            allocations[self.order[-1]] += remaining

        return allocations
