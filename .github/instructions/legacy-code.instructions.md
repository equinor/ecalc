---
applyTo: "src/libecalc/process/**,src/libecalc/energy/**,src/libecalc/ecalc_model/**"
---

# Legacy code

- Do not use `libecalc.application`, `libecalc.domain`, `libecalc.dto`, `libecalc.examples` or the legacy
  `libecalc.presentation` packages (`exporter`, `flow_diagram`, `json_result`, `simple_result`) as precedent for
  structure, naming or patterns in these packages.
- `tests/architectural_tests/` enforces which packages these may import. Run `uv run pytest -m arch` after changing
  imports.
