import json

import pytest
from jsonschema import Draft7Validator
from libecalc.input.validation.generate_json_schema import generate_json_schemas


class TestSchemas:
    def test_ecalc_model_json_schemas(self):
        schemas = generate_json_schemas(
            server_url="https://test.ecalc.equinor.com",
            docs_keywords_url="https://test.ecalc.equinor.com/docs/docs/modelling/keywords",
        )
        for schema in schemas:
            Draft7Validator.check_schema(schema=schema)

    @pytest.mark.snapshot
    def test_json_schema_changed(self, snapshot):
        """If this test fails you need to make sure the editor in the webapp behaves correctly, auto-completion and validation.

        When you have verified it works, you can run: poetry run pytest --snapshot-update
        See https://pypi.org/project/pytest-snapshot/ for more information.
        """
        schemas = generate_json_schemas(
            server_url="https://test.ecalc.equinor.com",
            docs_keywords_url="https://test.ecalc.equinor.com/docs/docs/modelling/keywords",
        )
        snapshot.assert_match(json.dumps(schemas, sort_keys=True, indent=4), snapshot_name="schemas.json")

    def test_temporal_property_placeholder(self):
        """
        Make sure we replace the type in temporal models correctly with ref. This can be removed when all json-schemas
        have been replaced with pydantic yaml models.

        See schema_helpers.replace_temporal_placeholder_property_with_legacy_ref
        """
        schemas = generate_json_schemas(
            server_url="https://test.ecalc.equinor.com",
            docs_keywords_url="https://test.ecalc.equinor.com/docs/docs/modelling/keywords",
        )
        energy_usage_model = schemas[0]["schema"]["definitions"]["YamlElectricityConsumer"]["properties"][
            "ENERGY_USAGE_MODEL"
        ]
        assert energy_usage_model["anyOf"] == [
            {
                "$ref": "https://test.ecalc.equinor.com/api/v1/schema-validation/energy-usage-model.json#properties/ENERGY_USAGE_MODEL"
            },
            {
                "type": "object",
                # TODO: We need to make a trade off now, either make parsing fail, or that the Open API JSON Schema does not indicate the date pattern we require as key
                # "patternProperties": {
                # "^\\d{4}\\-(0?[1-9]|1[012])\\-(0?[1-9]|[12][0-9]|3[01])$": {
                # "$ref": "https://test.ecalc.equinor.com/api/v1/schema-validation/energy-usage-model.json#properties/ENERGY_USAGE_MODEL"
                # }
                # },
                "additionalProperties": {
                    "$ref": "https://test.ecalc.equinor.com/api/v1/schema-validation/energy-usage-model.json#properties/ENERGY_USAGE_MODEL"
                },
            },
        ]
