import json
from pathlib import Path
from typing import List

from libecalc.dto.ecalc_model import SchemaSettings
from libecalc.input.validation import json_schemas

# This just needs to be a unique ID, it is required, but we do not need to have anything at that URI
# since we are embedding everything within one file
# Do not change this URI, since it has already been used in all json schemas
from libecalc.input.yaml_types.models.turbine import Turbine
from libecalc.input.yaml_types.variable import Variables
from pydantic import schema_of

BASE_URI = "$SERVER_NAME/api/v1/schema-validation"
JSON_SCHEMA_PATH = Path(json_schemas.__file__).resolve().parent
ROOT_JSON_SCHEMA_FILE_NAME = "ecalc-model.json"

VARIABLES_URI = f"{BASE_URI}/variables.json"


def get_template(schema: str, schema_name: str, is_root: bool = False) -> str:
    template = f'{{"uri": "{BASE_URI}/{schema_name}",\n'

    if is_root:
        template += '"fileMatch": ["*"],\n'
    else:
        # Match no files. This is all sub-schemas
        template += '"fileMatch": [],\n'

    template += f'"schema": {schema}}}'

    return template


def generate_json_schemas(server_url: str, docs_keywords_url: str) -> List[SchemaSettings]:
    schemas = []

    # First we get the root schema
    with open(JSON_SCHEMA_PATH / ROOT_JSON_SCHEMA_FILE_NAME) as root_model_file:
        root_model_schema = root_model_file.read()
        schema = get_template(
            schema=root_model_schema,
            schema_name="ecalc-model.json",
            is_root=True,
        )
        schemas.append(schema)

    # Then we just take the rest
    for json_schema_file in sorted([file for file in JSON_SCHEMA_PATH.iterdir() if file.suffix == ".json"]):
        if json_schema_file.name == "models-turbine.json":
            schema = schema_of(
                Turbine,
                by_alias=True,
                title="TURBINE",
                ref_template=f"{BASE_URI}/{json_schema_file.name}#/definitions/{{model}}",
            )
            schemas.append(get_template(json.dumps(schema), schema_name=json_schema_file.name, is_root=False))
        else:
            with open(json_schema_file) as schema_file:
                model_schema = schema_file.read()
                schema = get_template(
                    schema=model_schema,
                    schema_name=json_schema_file.name,
                    is_root=False,
                )
                schemas.append(schema)

    variables_schema = schema_of(
        Variables, by_alias=True, title="Variables", ref_template=f"{VARIABLES_URI}#/definitions/{{model}}"
    )

    # Patterned properties not supported in monaco-yaml, replace with additionalProperties.
    monaco_schema = {key: value for key, value in variables_schema.items() if key != "patternProperties"}

    variables_pattern_properties = list(variables_schema["patternProperties"].values())

    if len(variables_pattern_properties) > 1:
        raise ValueError("Multiple patternProperties is not handled.")

    monaco_schema["additionalProperties"] = variables_pattern_properties[0]
    schemas.append(get_template(schema=json.dumps(monaco_schema), schema_name="variables.json", is_root=False))

    processed_schemas = []
    for schema in schemas:
        content = schema.replace("$SERVER_NAME", server_url)
        content = content.replace("$ECALC_DOCS_KEYWORDS_URL", docs_keywords_url)
        processed_schemas.append(json.loads(content))

    return processed_schemas
