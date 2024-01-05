---
sidebar_position: 1
---
# FLUID_MODEL_TYPE

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md) :
[FLUID](/about/references/keywords_tree/MODELS/TYPE/FLUID/index.md) /
[FLUID_MODEL_TYPE](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/index.md)

## Description
`FLUID_MODEL_TYPE` defines how to describe the fluid composition in the fluid model. 
There are two ways to describe the composition, either as [PREDEFINED](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/PREDEFINED/index.md) or as 
a user defined [COMPOSITION](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/COMPOSITION/index.md).

To calculate the energy usage related to compression of a natural gas, 
information about the composition is needed, i.e. which components it consists of 
and the (mole) fraction of each. Typical components for natural gas are alkanes such as
methane, ethane, propane, butane, pentane, hexane in addition to water, nitrogen 
and carbone dioxide. Alkanes with seven or more carbon atoms may occur, but these 
are often just part of the liquid (oil) phase and not significant in dry gas
compression.

### Examples
Example where `EOS_MODEL` is defaulted to SRK and `GAS_TYPE` defaulted to MEDIUM:

~~~~~~~~yaml
MODELS:
  - NAME: fluid_model_reference_name
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
~~~~~~~~