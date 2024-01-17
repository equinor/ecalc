---
sidebar_position: 1
---
# GAS_TYPE

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md) :
[FLUID](/about/references/keywords_tree/MODELS/TYPE/FLUID/index.md) /
[GAS_TYPE](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/PREDEFINED/GAS_TYPE/index.md)

## Description
`GAS_TYPE` is used to define predefined fluid compositions for fluid models, when 
[FLUID_MODEL_TYPE](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/index.md) 
is set to PREDEFINED. The keyword is optional and defaults to `MEDIUM`.

Available predefined fluid compositions (with mole weights) are

- ULTRA_DRY (17.1 kg/kmol)
- DRY (18.3 kg/kmol)
- MEDIUM (19.4 kg/kmol) - default
- RICH (21.1 kg/kmol)
- ULTRA_RICH (24.6 kg/kmol)

### Example
~~~~~~~~yaml
MODELS:
  - NAME: fluid_model_reference_name
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    GAS_TYPE: ULTRA_DRY
~~~~~~~~