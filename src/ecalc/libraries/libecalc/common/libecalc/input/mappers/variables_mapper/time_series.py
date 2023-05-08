from datetime import datetime
from typing import List, NamedTuple


class TimeSeries(NamedTuple):
    reference_id: str
    time_vector: List[datetime]
    series: List[float]
