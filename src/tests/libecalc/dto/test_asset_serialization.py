from libecalc import dto

try:
    from pydantic.v1 import Protocol
except ImportError:
    from pydantic import Protocol


def test_serialization(all_energy_usage_models_dto):
    serialized_model = all_energy_usage_models_dto.ecalc_model.json()

    assert dto.Asset.parse_raw(serialized_model, proto=Protocol.json) == all_energy_usage_models_dto.ecalc_model
