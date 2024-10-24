---
title: How eCalc™ handles time
sidebar_position: 2
description: Time in eCalc™ - guide and description
---

eCalc™ does calculations between a global start date and a global end date. This global time period will be split into
many smaller time periods, where each of them follow immediately after each other, based on other dates encountered in
the YAML file and the requested output frequency. 

eCalc™ will first check if the global start and end dates are specified by the users, using the
[START](/about/references/START.md) and [END](/about/references/END.md) keywords in the YAML file. If the 
[START](/about/references/START.md) and [END](/about/references/END.md) keywords are not specified, the dates will be 
determined by the time series data given in [TIME_SERIES](/about/references/TIME_SERIES.md) together with the selected 
output frequency (which can be **Data defined**, **Yearly** or **Monthly**). This is done in the following way:
* Identify all the time series data which is given with [INFLUENCE_TIME_VECTOR](/about/references/INFLUENCE_TIME_VECTOR.md)
  set to True. The earliest date encountered within these time series data will be considered the global start date.
* If the output frequency is **Data defined**, the latest date encountered in the time series data with
  [INFLUENCE_TIME_VECTOR](/about/references/INFLUENCE_TIME_VECTOR.md) set to True is considered as the global end date.
  This is because eCalc™ will not have any other information about where the last period should stop.
* If the output frequency is **Yearly** or **Monthly**, the latest date encountered in the time series data with
  [INFLUENCE_TIME_VECTOR](/about/references/INFLUENCE_TIME_VECTOR.md) set to True will be considered as the start date
  of the final period of time in the model. This means that:
    * if the output frequency is **Yearly**, and the latest date found in the time series resources is 2020-01-01,
      the global end date will be set to 2021-01-01.
    * if the output frequency is **Yearly**, and the latest date found in the time series resources is 2020-06-01,
      the global end date will be set to 2021-01-01.
    * if the output frequency is **Monthly**, and the latest date found in the time series resources is 2020-06-01,
      the global end date will be set to 2020-07-01.

:::note
To have complete control over the period of time for which eCalc™ will do calculations, it is recommended to specify the
global start and end dates yourself using the [START](/about/references/START.md) and [END](/about/references/END.md) keywords
in the YAML file.
:::

The period of time between the global start and end dates, will be split into many smaller time periods. This is done
by finding:
* all other dates in all the time series data with
  [INFLUENCE_TIME_VECTOR](/about/references/INFLUENCE_TIME_VECTOR.md) set to True.
* all dates between the global start and end dates following the requested output frequency. If the output frequency is
  **Data defined**, no dates will be added. If the output frequency is **Yearly** or **Monthly**, the first day
  of each year or month between the global start and end dates will be added (if they are not already present in the
  time series input data).
* all dates defining temporal models in the YAML file (e.g. in 
  [ENERGY_USAGE_MODELS](/about/references/ENERGY_USAGE_MODELS.md), [FUEL](/about/references/FUEL.md) or
  [VARIABLES](/about/modelling/setup/variables.md)).

When all **N** dates are found and sorted, (**N-1**) time periods will be generated. The first time period will start
at the global start date and end at the next date in the sorted list. The second time period will start where the
previous ends (start is inclusive, end is exclusive), and so on until the last time period which will end at the global
end date.

The time series input given in the [TIME_SERIES](/about/references/TIME_SERIES.md) may not have values for all the
generated periods. Any missing values will be found using the chosen
[INTERPOLATION_TYPE](/docs/about/references/INTERPOLATION_TYPE). Be aware that if a time series has
[INFLUENCE_TIME_VECTOR](/about/references/INFLUENCE_TIME_VECTOR.md) set to False, there is a possibility that dates can
be dropped here.

:::note
The last row given for the variables in a single csv file is considered to be the values for the variables in the period
starting at that date. If no later dates are given in any other csv files, no [END](/about/references/END.md) date is
given and no output frequency is defined, the last row in that file is in reality irrelevant - it will not be used for
anything. But, if an end date is defined, either through an [END](/about/references/END.md) date or using **monthly** or
**yearly** output frequency, that last row will be the values for the variables in that additional added period of time.
:::

:::note
If one csv file ends several periods of time before another csv file, the last row in the first csv file will be the
:::
