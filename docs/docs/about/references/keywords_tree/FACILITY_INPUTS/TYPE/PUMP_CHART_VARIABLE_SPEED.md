---
sidebar_position: 4
---
# PUMP_CHART_VARIABLE_SPEED
[FACILITY_INPUTS](/about/references/keywords_tree/FACILITY_INPUTS/index.md) /
[TYPE](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/index.md) :
[PUMP_CHART_VARIABLE_SPEED](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/PUMP_CHART_VARIABLE_SPEED.md)

### Description
Pump chart data for variable speed (VSD) pump. The required fields are `SPEED`,
`RATE` and `HEAD`. Optionally (and most likely) `EFFICIENCY` and `UNITS` should be supplied as well.
(if not given, efficiency is set to 100%).

### Header Requirements
- `RATE`, `HEAD` and `SPEED` required.
- `EFFICIENCY`, `UNITS` optional.

### Format
~~~~~~~~yaml
FACILITY_INPUTS:
  - NAME: <FACILITY_INPUT_NAME>
    FILE: <path_to_file.csv>
    TYPE: PUMP_CHART_VARIABLE_SPEED
    UNITS:
        RATE: <rate unit, currently only AM3_PER_HOUR supported>
        HEAD: <polytropic head unit, M, KJ_PER_KG, JOULE_PER_KG supported>
        EFFICIENCY: <Pump efficiency unit FRACTION or PERCENTAGE.>
~~~~~~~~

## Examples
~~~~~~~~yaml
FACILITY_INPUTS:
  - NAME: a_single_speed_pump
    FILE: inputs/single_speed_pumpchart.csv
    TYPE: PUMP_CHART_SINGLE_SPEED
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: M
      EFFICIENCY: PERCENTAGE
      
  - NAME: a_variable_speed_pump
    FILE: inputs/variable_speed_pumpchart.csv
    TYPE: PUMP_CHART_VARIABLE_SPEED
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: M
      EFFICIENCY: PERCENTAGE

  - NAME: a_single_speed_pump_with_head_margin_applied
    FILE: inputs/single_speed_pumpchart.csv
    TYPE: PUMP_CHART_SINGLE_SPEED
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: M
      EFFICIENCY: PERCENTAGE
    HEAD_MARGIN: 10
~~~~~~~~
