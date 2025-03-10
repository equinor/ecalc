from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.emission import Emission
from libecalc.dto.types import FuelTypeUserDefinedCategoryType


class FuelType(EcalcBaseModel):
    name: str
    user_defined_category: FuelTypeUserDefinedCategoryType | None = Field(default=None, validate_default=True)
    emissions: list[Emission] = Field(default_factory=list)

    @field_validator("user_defined_category", mode="before")
    @classmethod
    def check_user_defined_category(cls, user_defined_category, info: ValidationInfo):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if user_defined_category is not None:
            if user_defined_category not in list(FuelTypeUserDefinedCategoryType):
                name_context_str = ""
                if (name := info.data.get("name")) is not None:
                    name_context_str = f"with the name {name}"

                raise ValueError(
                    f"CATEGORY: {user_defined_category} is not allowed for {cls.__name__} {name_context_str}. Valid categories are: {[str(fuel_type_user_defined_category.value) for fuel_type_user_defined_category in FuelTypeUserDefinedCategoryType]}"
                )

        return user_defined_category
