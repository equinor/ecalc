from typing import Union

from pydantic import BaseModel, ConfigDict

from libecalc.core.models.compressor.base import CompressorModel
from libecalc.core.models.pump import PumpModel


class ConsumerSystemComponent(BaseModel):
    name: str
    facility_model: Union[PumpModel, CompressorModel]
    model_config = ConfigDict(arbitrary_types_allowed=True)
