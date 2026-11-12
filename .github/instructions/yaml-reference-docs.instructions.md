---
applyTo: "src/libecalc/presentation/yaml/yaml_types/**,src/generate_yaml_asset_docs.py,src/libecalc/version.py,docs/docs/about/*-reference.mdx,docs/docs/yaml-changelog/**"
---

# YAML schema changes: lifecycle markers and generated docs

A change that adds, removes, renames or moves a YAML element (root or nested), or changes what it accepts, needs a
lifecycle marker and regenerated docs. A description-only change needs regenerated docs.

## Markers

From `yaml_types/yaml_version.py`, set on the field: `json_schema_extra=yaml_element_lifecycle(available_since=V4)`.

| Marker | Use for | Checked on load |
|---|---|---|
| `available_since=Vn` | new element | yes, rejected below n |
| `removed_since=Vn` | element no longer accepted | yes, rejected from n |
| `removed_field(title, removed_in, replaced_by=..., message=...)` | placeholder for a removed element, giving a helpful error | yes, always rejected |
| `changed_in=[(Vn, "text")]` | changed behaviour or accepted values | no, docs only |
| `deprecated_since=Vn` | discouraged but accepted | no, docs only |
| `required=True` | root `YamlAsset` element that must be present while available | yes |

- `replaced_by` is a path of YAML keywords, e.g. `("TIMELINE", "EVENTS")`, or a tuple of paths. Give it whenever
  something replaces the element; the keywords must match the titles in the generated docs. Use `message` only for
  what the path does not say.
- Put the marker on the field, also for nested fields. Fields inside a new element need no marker of their own.
- A new `TYPE` variant takes the marker in its own `model_config`. That marker only drives the docs and changelog;
  it is not checked on load.

## Version

- Only the major counts. The current major is `__yaml_version__` in `src/libecalc/version.py`.
- Use the current major unless a libeCalc release has shipped it; then the change belongs to the next major. If a
  `chore(main): release` PR is open, state the chosen major in the PR description so reviewers can confirm it.
- To bump: set `__yaml_version__` and add `Vn = Version(n, 0, 0)` in `yaml_version.py`.

## Docs

- From `src/`, run `uv run python generate_yaml_asset_docs.py` and include the regenerated
  `docs/docs/about/*-reference.mdx` and `docs/docs/yaml-changelog/` in the change. Never edit them by hand. CI fails
  if they are out of date.
- Check the generated example. Test builders feed it, and they skip `None`: start optional builder attributes as
  `None`, not `[]`.

- From `src/`, run `generate_fixture.py` that generates the nextgen example models (`src/libecalc/examples/nextgen/`) and their
documentation pages (`docs/docs/about/nextgen/examples/`) from the reference models in
`libecalc.fixtures.cases.nextgen.reference_model`. It is not run by pytest and must be run separately.
- Only the major counts. The current major is `__yaml_version__` in `src/libecalc/version.py`, to only update the examples
for the latest major version.
- Re-run it whenever the reference models, the YAML schema/version, or anything affecting the example output changes,
  and commit the regenerated files.
- Keep the script up to date when the reference model exports (`export_reference_models`, `export_example_pages`)
  change, e.g. new versions or new output locations.
- Never hand-edit the generated `model.yaml` files or example `.mdx` pages; change the reference models and regenerate.