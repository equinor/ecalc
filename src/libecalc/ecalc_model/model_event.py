from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum

from libecalc.common.ddd import value_object
from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.ids import EnergyUnitId


class EnergyUnitEventChangeType(StrEnum):
    """How an energy unit changes at an event.

    REBUNDLE keeps the same physical unit but gives it a new model/curve, mirroring the
    process pipeline REBUNDLE for compressors.
    """

    REBUNDLE = "REBUNDLE"


@value_object
class EnergyUnitModelEvent[ModelT]:
    """A dated, permanent change of an energy unit's model, e.g. a generator rebundle.

    ``change_to`` is the unit's model object (a fuel curve, an efficiency, ...), kept generic so
    the mechanism is not tied to any specific unit's model representation.

    Event dates are injected into the shared time vector, so a change date always coincides with a
    period boundary and the model switches exactly at that date.
    """

    change_target: EnergyUnitId
    change_type: EnergyUnitEventChangeType
    change_time: datetime
    change_to: ModelT


class DuplicateModelEventTimeException(EcalcValidationException):
    def __init__(self, change_times: Sequence[datetime]):
        dates = ", ".join(change_time.date().isoformat() for change_time in change_times)
        super().__init__(f"Only one model event is allowed per date. Got more than one event on {dates}.")


def validate_unique_change_times(model_events: Sequence[EnergyUnitModelEvent]) -> None:
    events_by_time = Counter(event.change_time for event in model_events)
    duplicate_times = sorted(change_time for change_time, count in events_by_time.items() if count > 1)
    if duplicate_times:
        raise DuplicateModelEventTimeException(duplicate_times)


def active_model[ModelT](
    initial_model: ModelT, model_events: Sequence[EnergyUnitModelEvent[ModelT]], at: datetime
) -> ModelT:
    """The model in use at ``at``: the latest event that has started, otherwise the initial model."""
    started_events = [event for event in model_events if event.change_time <= at]
    if not started_events:
        return initial_model
    return max(started_events, key=lambda event: event.change_time).change_to
