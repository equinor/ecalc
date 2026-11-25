import json

import pytest

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import (
    YamlAssetSchemaGenerator,
)

DOCS_KEYWORDS_URL = "https://example.com/docs/keywords"
DOCS_PLACEHOLDER = "ECALC_DOCS_KEYWORDS_URL"


@pytest.mark.snapshot
@pytest.mark.parametrize("nextgen", [False, True], ids=["legacy", "nextgen"])
def test_schema_snapshot(nextgen: bool, snapshot):
    schema = YamlAssetSchemaGenerator.get_schema(nextgen=nextgen, docs_keywords_url=DOCS_KEYWORDS_URL)

    snapshot_name = "ecalc-schema_nextgen.json" if nextgen else "ecalc-schema_legacy.json"
    snapshot.assert_match(json.dumps(schema, sort_keys=True, indent=4), snapshot_name=snapshot_name)


@pytest.mark.parametrize("nextgen", [False, True], ids=["legacy", "nextgen"])
def test_schema_replaces_all_docs_placeholders(nextgen: bool):
    serialized = json.dumps(YamlAssetSchemaGenerator.get_schema(nextgen=nextgen, docs_keywords_url=DOCS_KEYWORDS_URL))

    assert DOCS_PLACEHOLDER not in serialized
    assert DOCS_KEYWORDS_URL in serialized


def test_schema_keeps_docs_placeholders_without_url():
    serialized = json.dumps(YamlAssetSchemaGenerator.get_schema(nextgen=False))

    assert f"${DOCS_PLACEHOLDER}" in serialized


def test_legacy_schema_has_only_legacy_and_common_root_keys():
    schema = YamlAssetSchemaGenerator.get_schema(nextgen=False)

    assert {"FUEL_TYPES", "INSTALLATIONS", "MODELS", "TIME_SERIES", "FACILITY_INPUTS"} <= schema["properties"].keys()
    assert {"SHAFTS", "TIMELINE", "ENERGY_NETWORK", "YAML_VERSION"}.isdisjoint(schema["properties"])
    assert set(schema["required"]) == {"FUEL_TYPES", "INSTALLATIONS", "END"}


def test_nextgen_schema_has_only_nextgen_and_common_root_keys():
    schema = YamlAssetSchemaGenerator.get_schema(nextgen=True)

    assert {"SHAFTS", "TIMELINE", "ENERGY_NETWORK", "TIME_SERIES"} <= schema["properties"].keys()
    assert {"FACILITY_INPUTS", "FUEL_TYPES", "INSTALLATIONS", "MODELS", "YAML_VERSION"}.isdisjoint(schema["properties"])
    assert set(schema["required"]) == {"END"}


@pytest.mark.parametrize(
    "nextgen, excluded_definitions",
    [
        (False, {"YamlShaft", "YamlProcessPipeline", "YamlEnergyNetwork", "YamlPumpPipeline"}),
        (True, {"YamlInstallation", "YamlFuelType"}),
    ],
    ids=["legacy", "nextgen"],
)
def test_schema_only_has_definitions_for_its_format(nextgen: bool, excluded_definitions: set[str]):
    schema = YamlAssetSchemaGenerator.get_schema(nextgen=nextgen)

    assert excluded_definitions.isdisjoint(schema["$defs"])
