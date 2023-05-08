from typing import List

from libecalc.dto.base import EcalcBaseModel
from pydantic import Field


class SchemaSettings(EcalcBaseModel):
    uri: str
    fileMatch: List[str]
    ecalc_schema: dict = Field(alias="schema")
