from typing import List

from pydantic import Field

from libecalc.dto.base import EcalcBaseModel


class SchemaSettings(EcalcBaseModel):
    uri: str
    fileMatch: List[str]
    ecalc_schema: dict = Field(alias="schema")
