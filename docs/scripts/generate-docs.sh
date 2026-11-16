#!/usr/bin/env bash
# Generates the docs pages that are built from code, for the current version only.
# The output is not committed (see .gitignore), except the nextgen example model in src/libecalc/examples/nextgen/,
# which is library content and checked for drift in CI.
#
# Usage: docs/scripts/generate-docs.sh (from any directory). Requires uv and a synced project (uv sync).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

echo "Generating nextgen example model, example page and archive"
uv run python src/generate_fixture.py

echo "Generating process, energy and YAML reference, energy units and YAML changelog"
uv run python src/generate_yaml_asset_docs.py

echo "Generating CLI reference"
uv run typer src/ecalc_cli/main.py utils docs > docs/docs/about/getting_started/cli/cli_reference.md

echo "Generating JSON schema"
uv run python src/generate_json_schema.py > docs/docs/about/getting_started/yaml/ecalc_json_schema.json
