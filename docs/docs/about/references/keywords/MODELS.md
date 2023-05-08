# MODELS

[MODELS](MODELS)

## Description
Each element is specified in a list. These are later used as input to other models, or in the
[INSTALLATIONS](INSTALLATIONS) part of the setup by referencing their
[NAME](NAME).

This part of the setup specifies models not having any input data and/or multi level models, that is models which use
other models (from both [MODELS](MODELS) and from [FACILITY_INPUTS](FACILITY_INPUTS)).

## Format

~~~~~~~~yaml
MODELS:
  - NAME: <name of model, for reference>
    TYPE: <model type>
    <other keywords according to TYPE>
~~~~~~~~

## Supported Model types

The supported types are:

- `FLUID`
- `COMPRESSOR_CHART`
- `SINGLE_SPEED_COMPRESSOR_TRAIN`
- `SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN`
- `VARIABLE_SPEED_COMPRESSOR_TRAIN`
- `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`
- `TURBINE`
- `COMPRESSOR_WITH_TURBINE`


The documentation of each of these is found on the [Compressor Modelling](../../modelling/setup/models/compressor_modelling/compressor_models_types/) page.