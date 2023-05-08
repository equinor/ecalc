# CURVES

## Description

When using a detailed compressor model, it is necessary to specify the [COMPRESSOR CHART](../../modelling/setup/models/compressor_modelling/compressor_charts/index.md). This can be defined from a .csv file, or it can be defined directly in the YAML file. If it is defined directly in the YAML file,

In either case, the keyword `CURVES` needs to be used. If an .csv file is being used, under the `CURVES` keyword, `FILE` must be used. If specified directly in the YAML file, `SPEED`, `RATE`, `HEAD` and `EFFICIENCY` must be defined.

## Format

~~~~yaml
MODELS:
  - NAME: <name of chart, for reference>
    TYPE: COMPRESSOR_CHART
    ...
    CURVES:
      - SPEED: <shaft speed for this curve, a number>
        RATE: <list of rate values for this chart curve>
        HEAD: <list of polytropic head values for this chart curve>
        EFFICIENCY: <list of polytropic efficiency values for this chart curve>

  - NAME: <name of chart, for reference>
    TYPE: COMPRESSOR_CHART
    ... 
    CURVES:
       - FILE: <filepath to compressor curve>
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: predefined_single_speed_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: SINGLE_SPEED
    ...
    CURVE:
      - SPEED: 7500
        RATE: [2900, 3503, 4002, 4595.0]
        HEAD: [8412.9, 7996, 7363, 6127]
        EFFICIENCY: [0.72, 0.75, 0.74, 0.70]

  - NAME: compressor_chart
    TYPE: COMPRESSOR_CHART
    ... 
    CURVES:
       - FILE: compressor_chart.csv
~~~~
