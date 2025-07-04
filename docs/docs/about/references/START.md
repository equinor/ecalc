# START

[START](/about/references/START.md)

| Required | Child of                  | Children/Options                   |
|----------|---------------------------|------------------------------------|
| **No**   | `None`         | `None`   |

:::important
The value given as `START` is *inclusive* (and `END` is *exclusive*), meaning that the date specified is included in the simulation. If you e.g. specify the start date as `2020-01-01`,
and the `END` is `2021-01-01`, the interval given as mathematical notation is:

**[START, END)**
:::

## Description
The global start date for eCalc to begin energy and emission calculations. It is recommended that you have control
of which date you want data to be calculated and exported for, in particular when using LTP and FDE workflows.

If you specify 2020-01-01, the whole year of 2020 is included in the output. The hours, minutes and seconds
of the day are implicitly set to "00:00:00", so the counting starts from midnight on January 1st 2020.

You can provide a  date that is before the global time vector, but it is recommended to set it to the start of your timeseries data. Normally the
timeseries data provides this information directly, when specifying the first time step e.g. 2020-01-01, meaning that the data is valid from January 1st 2020,
but  data by default has  ([INTERPOLATION_TYPE](/about/references/INTERPOLATION_TYPE.md)), which means that it backfills data, and then we will know how far back
to backfill data (ie  defines this for the first period).

The cousin of is [END](/about/references/END.md) and have similar behaviour, but check the reference for details, to make sure you have the correct understanding.

If it is not specified, eCalc will make an educated *GUESS* on when the output data should start, but that may be incorrect, therefore it is recommended that you
stay in control of that to make sure you get correct output.

## Format
~~~~~~~~yaml
START: <YYYY-MM-DD>
~~~~~~~~

## Example
Given an input dataset from **01-01-2000 - 01-01-2040**, ignoring the first 20 years of data
can be achieved as follows:

~~~~~~~~yaml
START: 2020-01-01
~~~~~~~~

