---
applyTo: "src/libecalc/ecalc_model/**,src/libecalc/presentation/yaml/yaml_types/**,src/libecalc/presentation/yaml/mappers/**"
---

# Validation

- Validate in the domain model (`src/libecalc/ecalc_model`), not in the YAML types. The YAML types in
  `presentation/yaml/yaml_types` should only describe the shape of the input; custom pydantic validators there are a
  last resort. This includes rules such as unique names, which belong in the domain model.	
- It must not be possible to instantiate an invalid domain object: entities validate in `__init__` before assigning
  state, value objects (`@value_object`) validate in `__post_init__`. There is no separate `validate()` step.
- Check invariants an object can see on its own. Check rules across children in their owner. Rules across aggregates that are only referenced
  by id belong in the mapper or a domain service.
