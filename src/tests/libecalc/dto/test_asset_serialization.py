from libecalc import dto
from libecalc.fixtures import DTOCase


def test_serialization(all_energy_usage_models_dto: DTOCase):
    serialized_model = all_energy_usage_models_dto.ecalc_model.model_dump_json()

    assert dto.Asset.model_validate_json(serialized_model) == all_energy_usage_models_dto.ecalc_model
