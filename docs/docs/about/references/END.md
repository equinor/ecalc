# END

[END](/about/references/END.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `None`         | `None`   |

## Description
Global end date for eCalc to stop energy and emission calculations. It is recommended that you have control of which date you want data to be calculated and exported for.

If you specify the end date as 2080-01-01, the last period to be calculated is 2079 is included in the output. The hours, minutes and seconds of the day are implicitly set to "00:00:00", so the counting ends at midnight on January 1st 2080 (2079-12-31 23:59:59).

You can provide a date that is after the global time vector, but it is recommended to set it to the end of your timeseries data. Normally the timeseries do not provide this information directly. The last timestep provided in a timeseries is e.g. 2079-01-01, which would often mean that the data changed at that point,
and will e.g. be valid 1 year from then (if we work with YEARLY output frequency). To make sure that eCalc stops at the correct place, you should therefore specify the exclusive  date of the data.

The [START](/about/references/START.md) keyword have similar behaviour.

If END is not specified, eCalc will make an educated (but possibly incorrect) *guess* on when the output data should end.

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

