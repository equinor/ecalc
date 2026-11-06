# AGENTS.md

This directory (`libecalc/`) is a separate git repository containing the core domain library and CLI.

## Test Commands

Run from `libecalc/`:

```sh
python -m pytest                                    # Run all tests
python -m pytest path/to/test_file.py               # Single test file
python -m pytest path/to/test_file.py::test_func     # Single test function
```

Always exclude the `dockersnapshot` and `x86` markers when running locally — these tests require an x86 container
(snapshot generation) and will fail or be skipped-in-spirit on other architectures (e.g. Apple Silicon):

```sh
python -m pytest -m "not dockersnapshot and not x86"
```

Other markers (see `pyproject.toml`): `e2e`, `integtest`, `slow`, `snapshot`, `inlinesnapshot`, `arch`.

## YAML Schema Versioning

YAML input models carry a lifecycle via `yaml_element_lifecycle(...)` in
`src/libecalc/presentation/yaml/yaml_types/yaml_version.py`, set in a field's `json_schema_extra`:

- `available_since` / `removed_since`: the element is only accepted when the document's declared
  `YAML_VERSION` falls in `[available_since, removed_since)`. Enforced at runtime by
  `YamlAsset.validate_elements_available_for_version`, which walks the whole model tree
  (`get_unavailable_elements`) and checks every field that is **explicitly set**
  (`model_fields_set`), not just root fields.
- `required=True`: the element must be explicitly present for every version it's available in
  (checked separately, only for `YamlAsset`'s own root fields, via `get_required_field_names`).
- `for_documentation_only=True`: adds `"not": {}` to the generated JSON Schema so external editors
  reject the field. This is schema-generation-only — it does **not** gate runtime pydantic
  validation. Runtime gating is solely `available_since`/`removed_since`.
- `changed_in`: documentation-only marker, no runtime effect. Lists `(version, description)` pairs
  for behavioral changes that weren't an addition, deprecation or removal.
- `deprecated_since`: documentation-only marker, no runtime effect.

When bumping to a new major YAML version, update:

- `__yaml_version__` in `src/libecalc/version.py` (`current_yaml_version()`).

`LATEST_YAML_VERSION` is what test builders (`YamlAssetBuilder` in `src/libecalc/testing/yaml_builder.py`)
default to — forgetting to bump it means new version-gated fields will fail validation in any test
that relies on the builder's default version.

## Code Style

- **Python 3.12+**, package manager **uv**.
- **Ruff** for linting/formatting: line length 120.
- Type hints required throughout; modern syntax (`str | None`, `list[str]`, not `Optional`/`List`).
- Don't add comments or docstrings unless explicitly asked; prefer self-documenting code.

