from typing import Dict

from ecalc_cli.logger import logger
from pydantic import ValidationError

from libecalc import dto
from libecalc.presentation.yaml.validation_errors import DtoValidationError
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


class EmissionMapper:
    @staticmethod
    def from_yaml_to_dto(data: Dict) -> dto.Emission:
        if data.get("TAX") or data.get("QUOTA"):
            logger.warning("Emission tax and quota are deprecated. It will have no effect.")
        return dto.Emission(
            name=data.get(EcalcYamlKeywords.name),
            factor=data.get(EcalcYamlKeywords.emission_factor),
        )


class FuelMapper:
    @staticmethod
    def from_yaml_to_dto(fuel: Dict) -> dto.types.FuelType:
        try:
            if fuel.get("PRICE"):
                logger.warning("Fuel price is deprecated. It will have no effect.")

            return dto.types.FuelType(
                name=fuel.get(EcalcYamlKeywords.name),
                user_defined_category=fuel.get(EcalcYamlKeywords.user_defined_tag),
                emissions=[
                    EmissionMapper.from_yaml_to_dto(emission) for emission in fuel.get(EcalcYamlKeywords.emissions, [])
                ],
            )
        except ValidationError as e:
            raise DtoValidationError(data=fuel, validation_error=e) from e
