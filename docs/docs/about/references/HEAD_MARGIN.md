# HEAD_MARGIN

[FACILITY_INPUTS](/about/references/FACILITY_INPUTS.md) / 
[HEAD_MARGIN](/about/references/HEAD_MARGIN.md)

## Description
When calibrating pump charts to historical data, the head values at maximum speed
could be put in the cloud of data to be unbiased. However, eCalc will treat all
head values above the maximum defined area in the chart infeasible (i.e.,
outside pump capacity). To mitigate this when running through historical data for
power calibration, one can adjust the head margin with this keyword.

Calculated head values above maximum head values from the chart will be set equal to
maximum head values before power calculations **if** they are within the margin given.
Calculated head values larger than maximum + margin will still be infeasible.

## Format
The head margin can be specified in `mlc` (meter liquid column):

~~~~~~~~yaml
HEAD_MARGIN: <margin>
~~~~~~~~

## Example
~~~~~~~~yaml
    NAME: pump_name
    TYPE: PUMP_CHART_SINGLE_SPEED
    UNITS:
        HEAD: M
        RATE: AM3_PER_HOUR
        EFFICIENCY: PERCENTAGE
    FILE: <path_to_chart_file>.csv
    HEAD_MARGIN: 10.0
~~~~~~~~

