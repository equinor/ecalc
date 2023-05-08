# UNITS

## Description

`UNITS` is a keyword that can be specified for [PUMP](../../modelling/setup/facility_inputs/pump_modelling/pump_charts) and [COMPRESSOR CHARTS](../../modelling/setup/models/compressor_modelling/compressor_charts/). This is a requirement and **must** be specified.

For pumps this must be specified in `FACILITY_INPUTS`, whilst for compressors it must be within `MODELS`.

## Format

### Pumps

~~~~yaml
FACILITY_INPUTS:
  - NAME: <pump chart name>
    ...
    UNITS:
        RATE: <rate unit, currently only AM3_PER_HOUR supported>
        HEAD: <polytropic head unit, M, KJ_PER_KG, JOULE_PER_KG supported>
        EFFICIENCY: <Pump efficiency unit FRACTION or PERCENTAGE.>
~~~~

### Compressors

~~~~yaml
MODELS:
  - NAME: <name of chart, for reference>
    ...
    UNITS:
      RATE: <rate unit, currently only AM3_PER_HOUR supported>
      HEAD: <polytropic head unit, M, KJ_PER_KG, JOULE_PER_KG supported>
      EFFICIENCY: <polytropic efficiency unit, FRACTION and PERCENTAGE.>
    ....
~~~~

## Example

### Pumps

~~~~yaml
FACILITY_INPUTS:
  - NAME: single_speed_pump
    TYPE: PUMP_CHART_SINGLE_SPEED
    ...
    UNITS:
        RATE: AM3_PER_HOUR
        HEAD: M
        EFFICIENCY: PERCENTAGE
~~~~

### Compressors

~~~~yaml
MODELS:
  - NAME: predefined_variable_speed_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: VARIABLE_SPEED
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: M
      EFFICIENCY: FRACTION
    ...
~~~~
