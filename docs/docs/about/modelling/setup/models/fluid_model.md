---
title: Fluid model
sidebar_position: 1
description: Selecting a fluid model in eCalc
---

# Fluid model
To calculate the energy usage related to compression of a natural gas, information about the composition is needed, i.e.
which components it consist of and the (mole) fraction of each. Typical components for natural gas are alkanes such as
methane, ethane, propane, butane, pentane, hexane in addition to water, nitrogen and carbone dioxide. Alkanes with seven
or more carbon atoms may occur, but these are often just part of the liquid (oil) phase and not significant in dry gas
compression.

As the fluid is going through the compressor in a fluid dynamic process, the enthalpy changes, resulting in a new state
with increased pressure and temperature, and decreased volume. To estimate these changes, an equation-of-state (EOS)
model is used. The default EOS model in eCalc is SRK (Soave-Redlich-Kwong).

The GERG models (GERG 2008) are used to calculate enthalpy, gamma and density, whilst other properties such as molar mass
is based on either SRK or PR.

Available EOS models

- SRK (Soave-Redlich-Kwong)
- PR (Peng-Robinson)
- GERG_SRK
- GERG_PR

## Fluid model using predefined composition
Available predefined fluid compositions (with mole weights) are

- ULTRA_DRY (17.1 kg/kmol)
- DRY (18.3 kg/kmol)
- MEDIUM (19.4 kg/kmol)
- RICH (21.1 kg/kmol)
- ULTRA_RICH (24.6 kg/kmol)

### Format
~~~~~~~~yaml
MODELS:
  - NAME: <name of fluid model, for reference>
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: <eos model>
    GAS_TYPE: <name of a predefined composition>
~~~~~~~~

### Examples
Examples with predefined fluid

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
    EOS_MODEL: PR
    GAS_TYPE: ULTRA_DRY
~~~~~~~~

Example where EOS is defaulted to SRK and GAS_TYPE defaulted to MEDIUM

~~~~~~~~yaml
MODELS:
  - NAME: fluid_model_reference_name
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
~~~~~~~~

## Fluid model with user-specified composition
The composition is specified by setting the mole fraction of each component. Setting the mole fraction for **methane is
required**, all other components are optional and will be set to 0 if not specified. If methane is not part of your
composition, simply put 0.0 for it.

It is not important that the fractions sum to one as they will be normalized by eCalc. It is the relative amount of each
that will be important.

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

