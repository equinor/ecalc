---
title: Time periods in eCalc™
sidebar_position: 8
description: Time in eCalc™ - guide and description
---

# Time periods in eCalc™
eCalc™ does calculations between a global start date and a global end date. This global time period will be split into
many smaller time periods, where each of them follow immediately after each other, based on other dates encountered in
the YAML file and in the various time series resource files. 


## Finding the global start and end dates

The global start and end dates can be specified directly in the YAML file. 
eCalc™ will first check if the global start and end dates are specified by the users. This is done using the
[START](/about/references/START.md) and [END](/about/references/END.md) keywords in the YAML file. If the 
[START](/about/references/START.md) and [END](/about/references/END.md) keywords are not specified, the dates will be 
determined by the time series data given in [TIME_SERIES](/about/references/TIME_SERIES.md). The earliest date and latest date encountered within the 
time series data with [INFLUENCE_TIME_VECTOR](/about/references/INFLUENCE_TIME_VECTOR.md) set to True will be considered the global start date and global end 
date, respectively. 

:::note
Any dates defined in the YAML file (e.g. in [ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md)) will not
influence the global start and end dates.
:::

:::note
To have complete control over the period of time for which eCalc™ will do calculations, it is recommended to specify the
global start and end dates yourself using the [START](/about/references/START.md) and [END](/about/references/END.md) keywords
in the YAML file.
:::


## Splitting the global time period into smaller time periods
The period of time between the global start and end dates, will be split into many smaller time periods. This is done
by finding:
* all other dates in all the time series data that are between the global start and end dates, **and** has
  [INFLUENCE_TIME_VECTOR](/about/references/INFLUENCE_TIME_VECTOR.md) set to **True**.
* all dates defining temporal models in the YAML file (e.g. in 
  [ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md), [FUEL](/about/references/FUEL.md) or
  [VARIABLES](/about/modelling/setup/variables.md)) that are between the global start and end dates.

When all **N** dates are found and sorted, (**N-1**) time periods will be generated. The first time period will start
at the global start date and end at the next date in the sorted list. The second time period will start where the
previous ends (start is inclusive, end is exclusive), and so on until the last time period which will end at the global
end date.

The time series input given in the [TIME_SERIES](/about/references/TIME_SERIES.md) may not have values for all the
generated periods. Any missing values will be found using the chosen
[INTERPOLATION_TYPE](/docs/about/references/INTERPOLATION_TYPE). 


:::note
Be aware that when a time series has [INFLUENCE_TIME_VECTOR](/about/references/INFLUENCE_TIME_VECTOR.md) set to False, any dates found in the csv file that are
not already included in the global time vector, will be left out.
:::

:::note
The last row given for the variables in a single csv file is considered to be the values for the variables in the period
starting at that date. If no later dates are given in any other csv files, or no [END](/about/references/END.md) date is
given, the last row in that file is in reality irrelevant - it will not be used for
anything. But, if an end date is defined through the [END](/about/references/END.md) keyword, that last row will be the values for the 
variables in that additional added period of time.
:::

:::note
If one csv file ends several periods of time before another csv file, the last row in the first csv file will be
extrapolated. Either just for one period (if [EXTRAPOLATION](/docs/about/references/EXTRAPOLATION) is False), or for all
remaining periods (if [EXTRAPOLATION](/docs/about/references/EXTRAPOLATION) is True).
:::
