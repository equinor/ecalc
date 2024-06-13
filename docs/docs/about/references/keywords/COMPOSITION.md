# COMPOSITION

## Description

`COMPOSITION` is required to be specified for a model under the [MODELS](/about/references/keywords/MODELS.md) keyword
when the model is of [TYPE](/about/references/keywords/TYPE.md) `FLUID` and the [FLUID_MODEL_TYPE](/about/references/keywords/FLUID_MODEL_TYPE.md) is set to be `COMPOSITION`.
The composition is specified by setting the mole fraction of each component. The available components are:
      - water
      - nitrogen
      - CO2
      - methane
      - ethane
      - propane
      - i_butane
      - n_butane
      - i_pentane
      - n_pentane
      - n_hexane

Setting the mole fraction for **methane is required**, all other components are optional and will be set to 0 if
not specified. If methane is not part of your composition, simply put 0.0 for it.

It is not important that the fractions sum to one as they will be normalized by eCalc. It is the relative amount of
each that will be important.

### Format
~~~~~~~~yaml
MODELS:
  - NAME: <name of fluid model, for reference>
    TYPE: FLUID
    FLUID_MODEL_TYPE: COMPOSITION
    EOS_MODEL: <eos model>
    COMPOSITION:
      water: <mole fraction>
      nitrogen: <mole fraction>
      CO2: <mole fraction>
      methane: <mole fraction, required>
      ethane: <mole fraction>
      propane: <mole fraction>
      i_butane: <mole fraction>
      n_butane: <mole fraction>
      i_pentane: <mole fraction>
      n_pentane: <mole fraction>
      n_hexane: <mole fraction>
~~~~~~~~

### Example
~~~~~~~~yaml
MODELS:
  - NAME: <name of fluid model, for reference>
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
