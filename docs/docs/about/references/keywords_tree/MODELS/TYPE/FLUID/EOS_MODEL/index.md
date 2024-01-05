---
sidebar_position: 2
---
# EOS_MODEL

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md) :
[FLUID](/about/references/keywords_tree/MODELS/TYPE/FLUID/index.md) /
[EOS_MODEL](/about/references/keywords_tree/MODELS/TYPE/FLUID/EOS_MODEL/index.md)

## Description
`EOS_MODEL` is used to define which equation-of-state (EOS) to use in the fluid model.

As the fluid is going through the compressor in a fluid dynamic process, 
the enthalpy changes, resulting in a new state with increased pressure and temperature, 
and decreased volume. To estimate these changes, an EOS-model is used. 
Several EOS-models are available:

- SRK (Soave-Redlich-Kwong) - default
- PR (Peng-Robinson)
- GERG_SRK
- GERG_PR

### Format
~~~~~~~~yaml
MODELS:
  - NAME: <name of fluid model, for reference>
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: <eos model>
    GAS_TYPE: <name of a predefined composition>
~~~~~~~~
