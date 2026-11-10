from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from libecalc.common.ddd import value_object


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

    change_type: EnergyUnitEventChangeType
    change_time: datetime
    change_to: ModelT
