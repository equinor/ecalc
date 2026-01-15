from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from libecalc.common.string.string_utils import to_camel_case
from libecalc.domain.fuel import Fuel
from libecalc.dto.emission import Emission
from libecalc.dto.types import FuelTypeUserDefinedCategoryType


class EcalcBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class FuelType(EcalcBaseModel, Fuel):
    id: UUID
    name: str
    user_defined_category: FuelTypeUserDefinedCategoryType | None = Field(default=None, validate_default=True)
    emissions: list[Emission] = Field(default_factory=list)

    def get_id(self) -> UUID:
        return self.id

    def get_name(self) -> str:
        return self.name
