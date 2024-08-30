# EOS_MODEL

## Description

`EOS_MODEL` is required to be specified under the [MODELS](/about/references/MODELS.md) keyword when
the model is of [TYPE](/about/references/TYPE.md) `FLUID`.

The `EOS_MODEL` can be one of the following:
- SRK
- PR
- GERG_SRK
- GERG_PR

If the `EOS_MODEL` is not specified, it will be defaulted to `SRK`.

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
