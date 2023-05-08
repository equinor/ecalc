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
