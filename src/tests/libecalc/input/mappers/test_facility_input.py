from typing import Dict

import pytest

from libecalc import dto
from libecalc.dto.types import EnergyModelType
from libecalc.presentation.yaml.mappers.facility_input import FacilityInputMapper
from libecalc.presentation.yaml.validation_errors import DtoValidationError
from libecalc.presentation.yaml.yaml_entities import Resource
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


def _create_facility_input_data(typ: str, file: str, name: str) -> Dict:
    return {
        EcalcYamlKeywords.type: typ,
        EcalcYamlKeywords.file: file,
        EcalcYamlKeywords.name: name,
    }


class TestFacilityInputMapper:
    def test_generator_set_sampled(self):
        resources = {"generator_file_path": Resource(headers=["POWER", "FUEL"], data=[[0, 0], [0.4, 0.7], [1, 1]])}
        facility_input_mapper = FacilityInputMapper(resources=resources)
        generator_set_sampled = facility_input_mapper.from_yaml_to_dto(
            _create_facility_input_data(
                typ="ELECTRICITY2FUEL",
                file="generator_file_path",
                name="genset,",
            )
        )

        assert isinstance(generator_set_sampled, dto.GeneratorSetSampled)
        assert generator_set_sampled.typ == EnergyModelType.GENERATOR_SET_SAMPLED
        assert generator_set_sampled.headers == ["POWER", "FUEL"]
        assert generator_set_sampled.data == [
            [0, 0],
            [0.4, 0.7],
            [1, 1],
        ]

    def test_invalid_model(self):
        # pydantic does not match type, then validate. So this test will only fail because the data does not match
        # any of the EnergyModels. See https://github.com/samuelcolvin/pydantic/issues/619 for status on discriminated
        # unions, i.e. specify a discriminator so that we don't have to validate against all models
        facility_input_mapper = FacilityInputMapper(resources={"some-file": Resource(headers=[], data=[])})
        with pytest.raises(DtoValidationError):
            facility_input_mapper.from_yaml_to_dto(
                _create_facility_input_data(name="something", typ="wrong_type", file="some-file")
            )
