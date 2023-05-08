# INTERPOLATION_TYPE
 
[TIME_SERIES](TIME_SERIES.md) /
[INTERPOLATION_TYPE](INTERPOLATION_TYPE)

New in **v8.1**, previously known as `RATE_INTERPOLATION_TYPE` that was renamed to `INTERPOLATION_TYPE`.

## Description
:::caution Caution
Only valid for CSV data of source `MISCELLANEOUS`. For `TIME_SERIES` of [TYPE](TYPE)
`DEFAULT` the keyword is not allowed as input. The following applies:
- MISCELLANEOUS: Interpolation type is mandatory.
- DEFAULT: Interpolation type not allowed. Default `RIGHT` is used.

:::

:::caution Caution
Different data types may require different types of interpolation. While reservoir rates are
typically interpolated `RIGHT` or `LEFT`, other data such as pressure is often interpolated 
linearly (`LINEAR`). Data that should be interpolated differently must be specified in 
different input files, as it is not possible to have multiple interpolation types for vectors
within the same file.

:::

Rates are given at defined time steps in the data source but are in essence valid for a time
interval. The [INTERPOLATION_TYPE](INTERPOLATION_TYPE)
will determine how rates are interpolated between the given time steps.

- `LEFT`: The rate given at the current time step is defining the rate in the time interval between the current and
  previous time step. This is in data science also known as backwards filling of missing values.
- `RIGHT`: The rate given at the current time step is defining the rate in the time interval between the current and
  next time step. This is in data science also known as forward filling of missing values.
- `LINEAR`: The rate will be linearly interpolated between the time steps.

The plot below shows how the different choices for [INTERPOLATION_TYPE](INTERPOLATION_TYPE) works in practice.

![](/img/docs/interpolation_plot.png)

## Format

```yaml
INTERPOLATION_TYPE: <LEFT/RIGHT/LINEAR>
```

### Requirements
[INTERPOLATION_TYPE](INTERPOLATION_TYPE) has to be specified if
[TYPE](TYPE) is set to `MISCELLANEOUS`.

[INTERPOLATION_TYPE](INTERPOLATION_TYPE) can not be specified if [TYPE](TYPE) is set to `DEFAULT`.

## Example
See the [TIME_SERIES](TIME_SERIES.md) `time_series_format`.
