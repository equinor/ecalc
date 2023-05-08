from datetime import datetime
from typing import Optional

from libecalc.common.time_utils import Frequency
from libecalc.dto.base import EcalcBaseModel


class ResultOptions(EcalcBaseModel):
    start: Optional[datetime] = None
    end: Optional[datetime] = None

    output_frequency: Frequency = Frequency.NONE
