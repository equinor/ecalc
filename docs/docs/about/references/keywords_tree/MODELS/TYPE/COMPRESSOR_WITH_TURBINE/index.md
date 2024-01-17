---
sidebar_position: 8
---
# COMPRESSOR_WITH_TURBINE

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md): 
[COMPRESSOR_WITH_TURBINE](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_WITH_TURBINE/index.md)

### Description
Combining a compressor train and a turbine into one model:

To model a turbine driven compressor train, a compressor train model needs to be combined with a turbine model. The
calculated shaft power required for the compressor train, will then be the input of the turbine model to calculate
fuel usage.

## Format
~~~~~~~~yaml
MODELS:
  - NAME: <name of turbine model, for reference>
    TYPE: COMPRESSOR_WITH_TURBINE
    COMPRESSOR_MODEL: <reference to compressor train model defined in [MODELS](../references/keywords/MODELS) or [FACILITY_INPUTS](../references/keywords/FACILITY_INPUTS) (of type COMPRESSOR_TABULAR)>
    TURBINE_MODEL: <reference to a turbine model defined in [MODELS](../references/keywords/MODELS) (of type TURBINE)>
    POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
~~~~~~~~

## Examples
~~~~~~~~yaml
MODELS:
  - NAME: simplified_compressor_train_model_with_turbine
    TYPE: COMPRESSOR_WITH_TURBINE
    COMPRESSOR_MODEL: simplified_compressor_train_model
    TURBINE_MODEL: compressor_train_turbine
    POWER_ADJUSTMENT_CONSTANT: 10
~~~~~~~~

Turbine combined with presampled compressor model (`COMPRESSOR_TABULAR<COMPRESSOR_TABULAR  facility input type>`)

~~~~~~~~yaml
MODELS:
  - NAME: compressor_sampled_tabulated_model_with_turbine
    TYPE: COMPRESSOR_WITH_TURBINE
    COMPRESSOR_MODEL: compressor_sampled_tabulated_model
    TURBINE_MODEL: compressor_train_turbine
    POWER_ADJUSTMENT_CONSTANT: 10
~~~~~~~~

