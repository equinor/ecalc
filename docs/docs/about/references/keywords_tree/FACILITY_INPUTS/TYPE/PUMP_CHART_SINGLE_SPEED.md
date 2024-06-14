---
sidebar_position: 4
---
# PUMP_CHART_SINGLE_SPEED
[FACILITY_INPUTS](/about/references/keywords_tree/FACILITY_INPUTS/index.md) /
[TYPE](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/index.md) :
[PUMP_CHART_SINGLE_SPEED](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/PUMP_CHART_SINGLE_SPEED.md)

Pump chart data for single speed pump. The required fields are `RATE` and `HEAD`. Optionally (and most likely) `EFFICIENCY` and `UNITS` should be supplied as well.
(if not given, efficiency is set to 100%).

### Header Requirements
#### Required
- `RATE`
- `HEAD`

#### Optional
- `EFFICIENCY`, if not set the efficiency is assumed to be 100%.
- `SPEED`, if set all values must be equal.

Note that speed is not used in any way for single speed pumps and is only included here to allow the speed column to be
present in the input file without the run failing. There is still a check that all speeds are equal if speed is present
to avoid usage of the wrong pump model, i.e. avoid using the single speed model for variable speed pump chart data.

### Format
~~~~~~~~yaml
FACILITY_INPUTS:
  - NAME: <FACILITY_INPUT_NAME>
    FILE: <path_to_file.csv>
    TYPE: PUMP_CHART_SINGLE_SPEED
    UNITS:
        RATE: <rate unit, currently only AM3_PER_HOUR supported>
        HEAD: <polytropic head unit, M, KJ_PER_KG, JOULE_PER_KG supported>
        EFFICIENCY: <Pump efficiency unit FRACTION or PERCENTAGE.>
~~~~~~~~