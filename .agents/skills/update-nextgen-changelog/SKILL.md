---
name: update-nextgen-changelog
description: Adds NextGen changelog entries for eCalc YAML schema changes on the current branch and checks the generated docs. Use when a change adds, changes, deprecates or removes a YAML element, when the docs CI build fails, or when a reviewer asks for a changelog entry.
---

# Update NextGen changelog

Rules: `.github/instructions/yaml-reference-docs.instructions.md`. How to create entries: `changelog/README.md`.

1. Find the schema changes:
   ```bash
   git fetch -q origin main
   git diff origin/main...HEAD -- src/libecalc/presentation/yaml/yaml_types changelog/unreleased
   ```
   List each NextGen element that was added, changed, deprecated or removed and has no entry yet. If only
   descriptions changed, go to step 3.
2. Create the entries and notes as described in `changelog/README.md`.
3. Generate and build the docs, then check that every entry appears under Unreleased and that its links resolve.
4. Verify:
   ```bash
   uv run pytest -q tests/docs tests/libecalc/presentation/yaml tests/libecalc/integration/test_nextgen_example.py
   uv run basedpyright
   ```
5. Report the entries you added. Do not commit until the user has approved them.
