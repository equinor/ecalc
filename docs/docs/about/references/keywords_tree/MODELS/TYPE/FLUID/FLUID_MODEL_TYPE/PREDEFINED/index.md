---
sidebar_position: 1
---
# PREDEFINED

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md) /
[FLUID](/about/references/keywords_tree/MODELS/TYPE/FLUID/index.md) /
[FLUID_MODEL_TYPE](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/index.md) /
[PREDEFINED](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/PREDEFINED/index.md)

## Description
Use predefined fluid composition in fluid model. The different predefined fluids are defined 
in the keyword [GAS_TYPE](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/PREDEFINED/GAS_TYPE/index.md).

### Examples
Examples with predefined fluid:

~~~~~~~~yaml
MODELS:
  - NAME: fluid_model_reference_name
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: SRK
    GAS_TYPE: MEDIUM
~~~~~~~~

~~~~~~~~yaml
MODELS:
  - NAME: fluid_model_reference_name
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: SRK
    GAS_TYPE: ULTRA_DRY
~~~~~~~~


