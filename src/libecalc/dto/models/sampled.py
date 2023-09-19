from typing import List

from libecalc.dto.models.base import EnergyModel


class EnergyModelSampled(EnergyModel):
    headers: List[str]
    data: List[List[float]]
    # TODO: validate number of headers equals number of vectors
    # validate all vectors (in data) have equal length
