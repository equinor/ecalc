# CHART_TYPE

## Description

`CHART_TYPE` is a required to be specified under the [MODELS](/about/references/keywords/MODELS.md) keyword when
the model is of [TYPE](/about/references/keywords/TYPE.md) `COMPRESSOR_CHART`.

The `CHART_TYPE` can either be set to:
- SINGLE_SPEED
- VARIABLE_SPEED
- GENERIC_FROM_INPUT
- GENERIC_FROM_DESIGN_POINT


## Format

~~~~yaml
MODELS:
  - NAME: <name of model>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: <SINGLE_SPEED, VARIABLE_SPEED, GENERIC_FROM_INPUT or GENERIC_FROM_DESIGN_POINT>
    ...
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: compressor_chart_model_reference_name
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: SINGLE_SPEED
    ...
~~~~