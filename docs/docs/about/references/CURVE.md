# CURVE

## Description

When using a detailed single speed compressor model, it is necessary to specify the single speed [COMPRESSOR CHART](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md#user-defined-single-speed-compressor-chart). This can be defined from a .csv file, or it can be defined directly in the YAML file. 
In either case, the keyword `CURVE` needs to be used. If a .csv file is being used, under the `CURVE` keyword, `FILE` must be used. If specified directly in the YAML file, `SPEED`, `RATE`, `HEAD` and `EFFICIENCY` must be defined.

## Format

~~~~yaml
MODELS:
  - NAME: <name of chart, for reference>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: SINGLE_SPEED
    ...
    CURVE:
      - SPEED: <shaft speed for this curve, a number>
        RATE: <list of rate values for this chart curve>
        HEAD: <list of polytropic head values for this chart curve>
        EFFICIENCY: <list of polytropic efficiency values for this chart curve>

  - NAME: <name of chart, for reference>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: SINGLE_SPEED
    ... 
    CURVE:
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
    CURVE:
       - FILE: compressor_chart.csv
~~~~
