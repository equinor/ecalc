# INLET_TEMPERATURE

[MODELS](MODELS) / [INLET_TEMPERATURE](INLET_TEMPERATURE.md)

| Required | Child of      | Children/Options |
|----------|---------------|------------------|
| Yes      | [MODELS](MODELS.md)  | None             |

## Description
This is a keyword used in [COMPRESSOR MODELLING](../../modelling/setup/models/compressor_modelling/compressor_models_types/index.md). It is a necessary input parameter which describes the inlet temperature to a compressor stage. Temperature **must** be given in <sup>o</sup>C.

As of now, this is can only be given as a single value. Time-series are not accepted here.

## Format

~~~~~yaml
MODELS:
  - NAME: <model name>
    ...
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
    ...
~~~~~

## Example

~~~~~yaml
MODELS:
  - NAME: compressor_train
    ...
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 20 #degC
    ...
~~~~~
