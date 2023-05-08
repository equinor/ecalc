# EXTRAPOLATION
 
[TIME_SERIES](TIME_SERIES.md) / 
[EXTRAPOLATION](EXTRAPOLATION)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| N/A         | `TIME_SERIES`         | `None`   |

## Description
:::caution
Only valid for CSV data of type `MISCELLANEOUS`. For `TIME_SERIES` of [TYPE](TYPE)
`DEFAULT` the keyword is not supported as input, and the functionality is defaulted to `False`..
:::

Defines whether the rates in the source should be set to 0 after the last time step, or equal
to value at last time step after the time interval.

Not supported when [TYPE](TYPE) is set to `DEFAULT`.

| `TYPE` set to                        | `EXTRAPOLATION` default         |
|-------------------------------------------|--------------------------------------|
| `DEFAULT`                           | Not supported                        |
| `MISCELLANEOUS`                     | No default                           |

## Format
~~~~~~~~yaml
EXTRAPOLATION: <True/False>
~~~~~~~~

### Requirements
[EXTRAPOLATION](EXTRAPOLATION) has to be specified if 
[TYPE](TYPE) is set to `MISCELLANEOUS`.
[EXTRAPOLATION](EXTRAPOLATION) can not be specified if 
[TYPE](TYPE) is set to `DEFAULT`.

## Example
See the [TIME_SERIES](TIME_SERIES.md) `time_series_format`.


