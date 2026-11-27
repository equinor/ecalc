from datetime import datetime

from libecalc.common.ddd import value_object
from libecalc.common.time_utils import Period
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import InvalidEnergyNetworkInputError


@value_object
class InputSchedule:
    """Which candidate is active, as a function of time. `initial` covers everything before the first change.
    `changes` must already be sorted by change_time; callers building one from unordered declarations (e.g. a
    mapper reading dated YAML changes) must sort first.
    """

    initial: EnergyUnitId
    changes: tuple[tuple[datetime, EnergyUnitId], ...]  # (change_time, new_active_candidate), sorted by change_time

    def __post_init__(self) -> None:
        previous_time: datetime | None = None
        previous_candidate = self.initial
        for change_time, candidate_id in self.changes:
            if previous_time is not None and change_time <= previous_time:
                raise InvalidEnergyNetworkInputError(
                    f"INPUT_CHANGES must have strictly increasing dates, got {change_time} after {previous_time}"
                )
            if candidate_id == previous_candidate:
                raise InvalidEnergyNetworkInputError(
                    f"INPUT_CHANGES has a no-op switch to already-active input '{candidate_id}' at {change_time}"
                )
            previous_time = change_time
            previous_candidate = candidate_id

    def get_candidate_ids(self) -> frozenset[EnergyUnitId]:
        return frozenset((self.initial, *(candidate_id for _, candidate_id in self.changes)))

    def active_at(self, period: Period) -> EnergyUnitId:
        active = self.initial
        for change_time, candidate_id in self.changes:
            if change_time <= period.start:
                active = candidate_id
            else:
                break
        return active
