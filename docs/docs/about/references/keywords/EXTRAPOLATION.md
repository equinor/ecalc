# EXTRAPOLATION
 
[TIME_SERIES](/about/references/keywords/TIME_SERIES.md) / 
[EXTRAPOLATION](/about/references/keywords/EXTRAPOLATION.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| N/A         | `TIME_SERIES`         | `None`   |

## Description
:::caution
Only valid for `TIME_SERIES` of [TYPE](/about/references/keywords/TYPE.md) `MISCELLANEOUS`. For type
`DEFAULT` the keyword is not supported as input, and the functionality is defaulted to `False`.
:::

Defines whether the rates in the source should be set to 0 after the last time step (`False`), or equal
to value at last time step after the time interval (`True`).


## Format
~~~~~~~~yaml
EXTRAPOLATION: <True/False>
~~~~~~~~

### Requirements

| `TYPE` set to                       | `EXTRAPOLATION` default |
|-------------------------------------|-------------------------|
| `DEFAULT`                           | always `False`          |
| `MISCELLANEOUS`                     | `False`                 |

## Example
See the [TIME_SERIES](/about/references/keywords/TIME_SERIES.md) `time_series_format`.


