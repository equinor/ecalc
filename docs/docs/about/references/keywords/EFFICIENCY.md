# EFFICIENCY

## Description

`EFFICIENCY` is a keyword that is used defining [PUMP](../../modelling/setup/facility_inputs/pump_modelling/pump_charts) and [COMPRESSOR CHARTS](../../modelling/setup/models/compressor_modelling/compressor_charts/).
Efficiency can either be given as a fraction or percentage.

For compressors, it is used in two separate ways under the `MODELS` or section:

- Defining the `UNITS` of `EFFICIENCY`
- Defining the set of values for `EFFICIENCY` under `CURVES` section. Here, this **must** be given as a set of values whose length (number of variables) match the correlating `HEAD` and `RATE` values.

For pumps, it is defined under the `FACILITY_INPUTS` section.

## Format

### COMPRESSORS

~~~~~yaml
MODELS:
  - NAME: <compressor chart name>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: <compressor chart type>
    UNITS:
      ...
      EFFICIENCY: <FRACTION or PERCENTAGE>
    CURVES:
        ...
        EFFICIENCY: <set of values>
~~~~~

### PUMPS

~~~~~yaml
FACILITY_INPUTS:
  - NAME: <FACILITY_INPUT_NAME>
    FILE: <path_to_file.csv>
    TYPE: PUMP_CHART_SINGLE_SPEED
    UNITS:
        ...
        EFFICIENCY: <Pump efficiency unit FRACTION or PERCENTAGE.>
~~~~~

## Example

~~~~~yaml
MODELS:
  - NAME: predefined_variable_speed_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: VARIABLE_SPEED
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: M
      EFFICIENCY: FRACTION
    CURVES:
      - SPEED: 7500
        RATE: [2900, 3503, 4002, 4595.0]
        HEAD: [8412.9, 7996, 7363, 6127]
        EFFICIENCY: [0.72, 0.75, 0.74, 0.70]
~~~~~
