#!/usr/bin/env bash
# Generates the docs and starts the local dev server (http://localhost:3001/ecalc/).
# Installs the Python dependencies, and the npm dependencies if they are missing.
#
# Usage: docs/scripts/start-docs.sh [docusaurus start options] (from any directory). Requires uv, node and npm.
# Extra options are passed on to `docusaurus start`, e.g. `docs/scripts/start-docs.sh --no-open`.
# Re-run docs/scripts/generate-docs.sh to pick up changes in generated pages while the server is running.
set -euo pipefail

for tool in uv node npm; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "'$tool' is required but was not found on PATH." >&2
    exit 1
  fi
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
docs_dir="$repo_root/docs"

echo "==> Installing Python dependencies"
(cd "$repo_root" && uv sync --locked --all-extras --dev)

echo "==> Generating docs"
"$script_dir/generate-docs.sh"

if [[ ! -d "$docs_dir/node_modules" ]]; then
  echo "==> Installing docs dependencies"
  (cd "$docs_dir" && npm ci --ignore-scripts)
fi

echo "==> Starting dev server"
cd "$docs_dir"
exec npm run start -- "$@"
