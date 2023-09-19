from typing import Union

from libecalc.core.models.compressor.base import CompressorModel
from libecalc.core.models.pump import PumpModel
from pydantic import BaseModel


class ConsumerSystemComponent(BaseModel):
    name: str
    facility_model: Union[PumpModel, CompressorModel]

    class Config:
        arbitrary_types_allowed = True
