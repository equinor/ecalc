---
name: update-docs-markers
description: Adds YAML lifecycle markers (yaml_element_lifecycle, removed_field) for eCalc YAML schema changes on the current branch, picks the YAML version, and regenerates the YAML reference docs and YAML changelog so the docs CI check passes. Use when a change adds, removes, renames or moves a YAML element or changes what it accepts, when the docs CI reports out-of-date YAML documentation, or when a reviewer asks for lifecycle markers or generate_yaml_asset_docs.py.
---

# Update docs markers

The rules are in `.github/instructions/yaml-reference-docs.instructions.md`. Read it first; this
skill is the workflow.

## Workflow

1. **Find the schema changes** on the branch:
   ```bash
   git fetch -q origin main
   git diff origin/main...HEAD -- src/libecalc/presentation/yaml/yaml_types
   ```
   List each YAML element (root or nested) that was added, removed, renamed or moved, or whose accepted values or
   behaviour changed. Description-only changes need no marker; go to step 4.

2. **Pick the YAML version** (major only):
   ```bash
   grep "__yaml_version__ =" src/libecalc/version.py
   git fetch -q --tags origin
   git show "$(git describe --tags --abbrev=0 --match 'v*' origin/main)":src/libecalc/version.py | grep "__yaml_version__ ="
   gh pr list --repo equinor/ecalc --state open --json number,title \
     --jq '.[] | select(.title | startswith("chore(main): release")) | "\(.number) \(.title)"'
   ```
   - The last release has an older major than main: use the current major.
   - The last release has the same major as main: that major has shipped. Bump it as the rule describes, and use
     the new major.
   - A release PR is open: the branch may merge after it. Tell the user which major you chose and why, and state it
     in the PR description so reviewers can confirm it.

3. **Add the markers**, choosing the marker from the rule's table. Each element in step 1 gets one; fields inside a
   new element do not.

4. **Regenerate the docs**:
   ```bash
   (cd src && uv run python generate_yaml_asset_docs.py)
   git diff --stat -- docs/docs/about/nextgen
   ```

5. **Check the generated docs**:
   - The vN changelog lists each element under Added, Changed or Removed, and `replaced_by` links resolve.
   - The element has its badge in the reference page.
   - The generated example shows no empty placeholders such as `KEY: []`. If it does, fix the test builder.

6. **Verify**:
   ```bash
   uv run pytest -q tests/libecalc/presentation/yaml tests/libecalc/energy
   uv run basedpyright
   ```
   A test that pins an older `with_yaml_version(...)` and uses the new element now fails by design. Raise the
   version in that test, or keep the old version if the test is about the older YAML.

7. **Report** the markers added (element, marker, version), the version decision and the docs files changed. Do not
   commit or push until the user has approved it.
