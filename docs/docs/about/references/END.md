# END

[END](/about/references/END.md)

| Required | Child of                  | Children/Options                   |
|----------|---------------------------|------------------------------------|
| **Yes**  | `None`         | `None`   |

:::info
- eCalc version 10.0.0: `END` is required since v10.0.0. < v10.0.0 the `END` keyword was optional, but it is now required to specify the end date of the simulation.
:::

:::important
The value given as `END` is *exclusive*, ie. the date specified is (just) not included in the simulation.

Conversely to `END` being *exclusive*, the `START` keyword is *inclusive*, meaning that the date specified as `START` is included in the simulation. If you are
used to mathematical notation, it is specified as:

**[START, END)**

:::

## Description
Global end date for eCalc to stop energy and emission calculations. This date is **required** to specify in the YAML file.

If you specify the end date as 2080-01-01, the last period to be calculated is 2079 is included in the output.
The hours, minutes and seconds of the day are implicitly set to "00:00:00", so the counting ends at midnight on
January 1st 2080 (2079-12-31 23:59:59). The same applies if you specify only the year, e.g. 2080, which is equivalent to 2080-01-01.

You can provide a date that is after the global time vector, but it is recommended to set it to the end of your
timeseries data. Normally the timeseries do not provide this information directly. The last timestep provided in a
timeseries is e.g. 2079-01-01, which would often mean that the data changed at that point, and will e.g. be valid 1
year from then. To make sure that eCalc stops at the correct place, you have to specify the exclusive date of the data.

The [START](/about/references/START.md) keyword have similar behaviour.


## Format
~~~~~~~~yaml
END: <YYYY-MM-DD>
~~~~~~~~

## Example
Given an input dataset from **01-01-2000 - 01-01-2040**, ignoring the last 20 years of data
can be achieved as follows:

~~~~~~~~yaml
END: 2020-01-01
~~~~~~~~

