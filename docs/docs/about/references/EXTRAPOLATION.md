# EXTRAPOLATION
 
[TIME_SERIES](/about/references/TIME_SERIES.md) / 
[EXTRAPOLATION](/about/references/EXTRAPOLATION.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| N/A         | `TIME_SERIES`         | `None`   |

## Description {/* #description */}
:::caution
Only valid for `TIME_SERIES` of [TYPE](/about/references/TYPE.md) `MISCELLANEOUS`. For type
`DEFAULT` the keyword is not supported as input, and the functionality is defaulted to `False`.
:::

Defines whether the rates in the source should be set to 0 after the last time step (`False`), or equal
to value at last time step after the time interval (`True`).


## Format {/* #format */}
~~~~~~~~yaml
EXTRAPOLATION: <True/False>
~~~~~~~~

### Requirements {/* #requirements */}

| `TYPE` set to                       | `EXTRAPOLATION` default |
|-------------------------------------|-------------------------|
| `DEFAULT`                           | always `False`          |
| `MISCELLANEOUS`                     | `False`                 |

## Example {/* #example */}
See the [TIME_SERIES](/about/references/TIME_SERIES.md) `time_series_format`.


