# FLUID_MODEL_TYPE

## Description {/* #description */}

`FLUID_MODEL_TYPE` is a required to be specified under the [MODELS](/about/references/MODELS.md) keyword when
the model is of [TYPE](/about/references/TYPE.md) `FLUID`.

The `FLUID_MODEL_TYPE` can either be set to `PREDEFINED` or to `COMPOSITION`.

## Format {/* #format */}

~~~~yaml
MODELS:
  - NAME: <name of model>
    TYPE: FLUID
    ...
    FLUID_MODEL_TYPE: <PREDEFINED or COMPOSITION>
~~~~

## Example {/* #example */}

~~~~yaml
MODELS:
  - NAME: fluid_model_reference_name
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: SRK
    GAS_TYPE: MEDIUM
~~~~
