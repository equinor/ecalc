# HEAD

## Description

`HEAD` is a keyword that is used defining [PUMP](/about/modelling/setup/facility_inputs/pump_modelling/pump_charts.md) and [COMPRESSOR CHARTS](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md).
Head can either be given as a M, KJ_PER_KG, JOULE_PER_KG.

For compressors, it is used in two separate ways under the `MODELS` or section:

- Defining the `UNITS` of `HEAD`
- Defining the set of values for `HEAD` under `CURVES` section. Here, this **must** be given as a set of values whose length (number of variables) match the correlating `EFFICIENCY` and `RATE` values.

For pumps, it is defined under the `FACILITY_INPUTS` section.

## Format

### COMPRESSORS

~~~~~yaml
MODELS:
  - NAME: <name of chart, for reference>
    ...
    UNITS:
      HEAD: <polytropic head unit, M, KJ_PER_KG, JOULE_PER_KG supported>
      ...
    ....
~~~~~

### PUMPS

~~~~~yaml
FACILITY_INPUTS:
  - NAME: <pump chart name>
    ...
    UNITS:
        HEAD: <polytropic head unit, M, KJ_PER_KG, JOULE_PER_KG supported>
        ...
~~~~~

## Example

### COMPRESSORS

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
