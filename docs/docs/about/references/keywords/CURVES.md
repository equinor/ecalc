# CURVES

## Description

When using a detailed variable speed compressor model, it is necessary to specify the variable speed [COMPRESSOR CHART](../../modelling/setup/models/compressor_modelling/compressor_charts/index.md#user-defined-variable-speed-compressor-chart). This can be defined from a .csv file, or it can be defined directly in the YAML file. 
In either case, the keyword `CURVES` needs to be used, and curves for at least two different speeds must be defined. If a .csv file is being used, under the `CURVES` keyword, `FILE` must be used. If specified directly in the YAML file, `SPEED`, `RATE`, `HEAD` and `EFFICIENCY` must be defined for each speed.

## Format

~~~~yaml
MODELS:
  - NAME: <name of chart, for reference>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: VARIABLE_SPEED
    ...
    CURVES:
      - SPEED: <shaft speed for this curve, a number>
        RATE: <list of rate values for this chart curve>
        HEAD: <list of polytropic head values for this chart curve>
        EFFICIENCY: <list of polytropic efficiency values for this chart curve>
      - SPEED: <shaft speed for this curve, a number>
        RATE: <list of rate values for this chart curve>
        HEAD: <list of polytropic head values for this chart curve>
        EFFICIENCY: <list of polytropic efficiency values for this chart curve>

  - NAME: <name of chart, for reference>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: VARIABLE_SPEED
    ... 
    CURVES:
       - FILE: <filepath to compressor curve>
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: predefined_variable_speed_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: VARIABLE_SPEED
    ...
    CURVES:
      - SPEED: 7500
        RATE: [2900, 3503, 4002, 4595.0]
        HEAD: [8412.9, 7996, 7363, 6127]
        EFFICIENCY: [0.72, 0.75, 0.74, 0.70]
      - SPEED: 9886
        RATE: [3708, 4502, 4993.6, 5507, 5924]
        HEAD: [13845, 13182, 12425, 11276, 10054]
        EFFICIENCY: [ 0.72, 0.75, 0.748, 0.73, 0.70]

  - NAME: compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: VARIABLE_SPEED
    ... 
    CURVES:
       - FILE: compressor_chart.csv
~~~~
