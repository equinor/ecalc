# GAS_TYPE

## Description

`GAS_TYPE` is required to be specified under the [MODELS](/about/references/keywords/MODELS.md) keyword when
the model is of [TYPE](/about/references/keywords/TYPE.md) `FLUID` and the [FLUID_MODEL_TYPE](/about/references/keywords/FLUID_MODEL_TYPE.md)
is `PREDEFINED`. Available gas types are:

- ULTRA_DRY
- DRY
- MEDIUM
- RICH
- ULTRA_RICH

If no `GAS_TYPE` is specified, it will be defaulted to `MEDIUM`.


## Format

~~~~yaml
MODELS:
  - NAME: <name of model>
    TYPE: FLUID
    ...
    EOS_MODEL: <SRK/PR/GERG_SRK/GERG_PR>
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
