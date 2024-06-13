# FLUID_MODEL_TYPE

## Description

`FLUID_MODEL_TYPE` is a required to be specified under the [MODELS](/about/references/keywords/MODELS.md) keyword when
the model is of [TYPE](/about/references/keywords/TYPE.md) `FLUID`.

The `FLUID_MODEL_TYPE` can either be set to `PREDEFINED` or to `COMPOSITION`.

## Format

~~~~yaml
MODELS:
  - NAME: <name of model>
    TYPE: FLUID
    ...
    FLUID_MODEL_TYPE: <PREDEFINED or COMPOSITION>
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: fluid_model_reference_name
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: SRK
    GAS_TYPE: MEDIUM
~~~~
