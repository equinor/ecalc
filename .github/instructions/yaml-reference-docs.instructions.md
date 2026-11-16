---
applyTo: "src/libecalc/presentation/yaml/yaml_types/**,src/generate_yaml_asset_docs.py,src/generate_fixture.py,src/libecalc/version.py,src/libecalc/fixtures/cases/nextgen/reference_model/**"
---

# YAML schema changes: lifecycle markers and generated docs

A change that adds, removes, renames or moves a YAML element (root or nested), or changes what it accepts, needs a
lifecycle marker. The docs are generated from the markers and descriptions.

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

- The docs pages are generated in CI for the current version by `docs/scripts/generate-docs.sh`, and are not
  committed: the reference pages, energy units and `yaml-changelog.md` in `docs/docs/about/nextgen/`, the example page
  `docs/docs/about/nextgen/examples.mdx` and its zip, the CLI reference and the JSON schema. Docs for previous versions
  are kept in their published builds.
- Run `docs/scripts/generate-docs.sh` to check the generated pages locally, and build the docs (`cd docs && npm run
  build`) to catch broken links. Never edit the generated pages by hand; change the markers, descriptions or
  generators.
- Check the generated example. Test builders feed it, and they skip `None`: start optional builder attributes as
  `None`, not `[]`.

## Example model

- The nextgen example is built from the reference model in `libecalc.fixtures.cases.nextgen.reference_model` (model
  builder plus the CSVs in `data/`). Nothing generated from it is committed.
- `src/generate_fixture.py` (run by the script above) renders `model.yaml` and the CSVs into
  `docs/docs/about/nextgen/examples.mdx`, and writes the downloadable zip.
- `tests/libecalc/integration/test_nextgen_example.py` exports the model to a temporary folder, loads it and validates
  it, so a broken reference model fails the library tests.
- Change the reference model, never the generated output.
