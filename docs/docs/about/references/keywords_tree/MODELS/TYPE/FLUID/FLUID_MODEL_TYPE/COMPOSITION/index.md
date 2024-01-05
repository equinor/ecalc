---
sidebar_position: 2
---
# COMPOSITION

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md) :
[FLUID](/about/references/keywords_tree/MODELS/TYPE/FLUID/index.md) /
[FLUID_MODEL_TYPE](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/index.md) :
[COMPOSITION](/about/references/keywords_tree/MODELS/TYPE/FLUID/FLUID_MODEL_TYPE/COMPOSITION/index.md)

## Description
Use user defined fluid composition in fluid model.

The composition is specified by setting the mole fraction of each component. Setting the mole fraction for **methane is
required**, all other components are optional and will be set to 0 if not specified. If methane is not part of your
composition, simply put 0.0 for it.

It is not important that the fractions sum to one as they will be normalized by eCalc. It is the relative amount of each
that will be important.

### Example
~~~~~~~~yaml
MODELS:
  - NAME: my_fluid_model
    TYPE: FLUID
    FLUID_MODEL_TYPE: COMPOSITION
    EOS_MODEL: srk
    COMPOSITION:
      water: 0.1
      nitrogen: 0.74373
      CO2: 2.415619
      methane: 85.60145
      ethane: 6.707826
      propane: 2.611471
      i_butane: 0.45077
      n_butane: 0.691702
      i_pentane: 0.210714
      n_pentane: 0.197937
      n_hexane: 0.368786
~~~~~~~~



