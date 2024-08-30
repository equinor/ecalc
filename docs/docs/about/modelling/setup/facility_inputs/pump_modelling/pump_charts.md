# Pump chart

Energy usage for pumps is not based on pre-sampled data between rates,
pressures and energy usage, but on **equations and the pump chart** defining the pumps.

There are two types of pump models supported:
- Variable speed pumps
- Single speed pumps

The pump chart defines the pump's operational area. When rates below minimum flow
(a point with the lowest rate for a single speed pump and a line defined by the lowest rate vs.
head for each speed for variable speed) are requested, the rate is projected up and
evaluated at minimum flow to mimic the `ASV` (anti-surge valve).

For heads below minimum head/minimum speed, i.e., when the requested pressure
difference between the outlet and the inlet is smaller than the minimum pressure difference,
the head will be lifted up to minimum head to mimic that the pump will then be run on
its minimum speed and the pressure will be choked back downstream of the pump.
For single speed pumps, the minimum speed/minimum head curve is the same as
the head vs. rate curve.

:::tip Tip
When calibrating pump charts to historical data, the head values for maximum speed could be
put in the cloud of data to be unbiased. However, eCalc will treat all head values above the
maximum defined in the chart as infeasible (outside pump capacity). 

To mitigate this when
running through historical data for power calibration, the keyword [HEAD_MARGIN](/about/references/HEAD_MARGIN.md) may be used to move points outside capacity (but inside the margin) to the capacity limit.
:::

## PUMP_CHART_SINGLE_SPEED

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
        HEAD: <polytropic head unit, only M supported>
        EFFICIENCY: <Pump efficiency unit FRACTION or PERCENTAGE.>
~~~~~~~~

## PUMP_CHART_VARIABLE_SPEED
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
        HEAD: <polytropic head unit, only M supported>
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
