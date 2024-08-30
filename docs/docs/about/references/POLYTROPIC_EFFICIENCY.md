# POLYTROPIC_EFFICIENCY

## Description

`POLYTROPIC_EFFICIENCY` is required to be specified under the [MODELS](/about/references/MODELS.md) keyword when
the model is of [TYPE](/about/references/TYPE.md) `COMPRESSOR_CHART` **and** the [CHART_TYPE](/about/references/CHART_TYPE.md)
is either `GENERIC_FROM_INPUT`or `GENERIC_FROM_DESIGN_POINT`. The polytropic efficiency will be a fixed number for all
rate/head values in the compressor chart.


## Format

~~~~yaml
MODELS:
  - NAME: <name of model>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: <GENERIC_FROM_INPUT or GENERIC_FROM_DESIGN_POINT>
    POLYTROPIC_EFFICIENCY: <polytropic efficiency of the compressor (fixed number)>
    UNITS:
      EFFICIENCY: <polytropic efficiency unit, FRACTION and PERCENTAGE.>
    ...
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: compressor_chart_model_reference_name
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: GENERIC_FROM_INPUT
    POLYTROPIC_EFFICIENCY: 0.75
    UNITS:
      EFFICIENCY: FRACTION
    ...
~~~~