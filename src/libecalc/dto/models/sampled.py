from typing import List, Optional

from pydantic import confloat
from pydantic.class_validators import root_validator

from libecalc.dto.models.base import EnergyModel
from libecalc.dto.types import EnergyUsageType


class EnergyModelSampled(EnergyModel):
    headers: List[str]
    data: List[List[float]]
    # TODO: validate number of headers equals number of vectors
    # validate all vectors (in data) have equal length
