---
sidebar_position: 1
---
# FLUID

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md) : 
[FLUID](/about/references/keywords_tree/MODELS/TYPE/FLUID/index.md)

## Description
The keyword FLUID is used to describe a fluid, which is necessary when defining a compressor model. 
The fluid has several attributes:

[FLUID_MODEL_TYPE](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/index.md) is a required attribute and defines how to describe the fluid composition, 
either as [PREDEFINED](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/PREDEFINED/index.md) or as a user defined [COMPOSITION](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/COMPOSITION/index.md). When using a predefined 
composition, it can be defined by the optional keyword 
[GAS_TYPE](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/PREDEFINED/GAS_TYPE/index.md). 

[EOS_MODEL](/about/references/keywords_tree/MODELS/TYPE/FLUID/EOS_MODEL/index.md), the equation-of-state used to describe pressure-, temperature- and volume changes, 
is optional.

How a fluid model is defined is 
described in further detail in [FLUID_MODEL](/about/references/keywords/FLUID_MODEL.md)

### Format
Predefined composition:

~~~~~~~~yaml
MODELS:
  - NAME: <name of fluid model, for reference>
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: <eos model>
    GAS_TYPE: <name of a predefined composition>
~~~~~~~~

User defined composition:
~~~~~~~~yaml
MODELS:
  - NAME: <name of fluid model, for reference>
    TYPE: FLUID
    FLUID_MODEL_TYPE: COMPOSITION
    EOS_MODEL: <eos model>
    COMPOSITION:
      methane: <mole fraction, required>
      water: <mole fraction>
      nitrogen: <mole fraction>
      CO2: <mole fraction>
      ethane: <mole fraction>
      ...
~~~~~~~~

