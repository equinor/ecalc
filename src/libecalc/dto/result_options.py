from datetime import datetime

from libecalc.common.time_utils import Frequency
from libecalc.dto.base import EcalcBaseModel


class ResultOptions(EcalcBaseModel):
    start: datetime | None = None
    end: datetime | None = None

    output_frequency: Frequency = Frequency.NONE
