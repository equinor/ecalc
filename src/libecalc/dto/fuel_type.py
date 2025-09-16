from uuid import UUID

from pydantic import Field

from libecalc.domain.fuel import Fuel
from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.emission import Emission
from libecalc.dto.types import FuelTypeUserDefinedCategoryType


class FuelType(EcalcBaseModel, Fuel):
    id: UUID
    name: str
    user_defined_category: FuelTypeUserDefinedCategoryType | None = Field(default=None, validate_default=True)
    emissions: list[Emission] = Field(default_factory=list)

    def get_id(self) -> UUID:
        return self.id

    def get_name(self) -> str:
        return self.name
