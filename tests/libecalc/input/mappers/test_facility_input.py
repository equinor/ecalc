from libecalc.common.energy_model_type import EnergyModelType
from libecalc.presentation.yaml.mappers.facility_input import FacilityInputMapper
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlGeneratorSetModel
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel


class TestFacilityInputMapper:
    def test_generator_set_sampled(self):
        resources = {"generator_file_path": MemoryResource(headers=["POWER", "FUEL"], data=[[0, 0.4, 1], [0, 0.7, 1]])}
        facility_input_mapper = FacilityInputMapper(resources=resources)
        generator_set_sampled = facility_input_mapper.from_yaml_to_dto(
            YamlGeneratorSetModel(
                type="ELECTRICITY2FUEL",
                file="generator_file_path",
                name="genset",
            )
        )

        assert isinstance(generator_set_sampled, GeneratorSetModel)
        assert generator_set_sampled.typ == EnergyModelType.GENERATOR_SET_SAMPLED
        assert generator_set_sampled.headers == ["POWER", "FUEL"]
        assert generator_set_sampled.data == [[0, 0.4, 1], [0, 0.7, 1]]
