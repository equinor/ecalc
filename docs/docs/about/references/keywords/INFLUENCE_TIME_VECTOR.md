# INFLUENCE_TIME_VECTOR

[TIME_SERIES](TIME_SERIES.md) /
[INFLUENCE_TIME_VECTOR](INFLUENCE_TIME_VECTOR.md)

## Description

Determines if the time steps in this input source will contribute to the global time vector.

If not specified, this will be defaulted to `TRUE`.
It is a requirement that at least one time vector has an `INFLUENCE_TIME_VECTOR` of `TRUE`.

## Format

~~~~~~~~yaml

INFLUENCE_TIME_VECTOR: <True/False>
~~~~~~~~

## Example

See the [TIME_SERIES](TIME_SERIES.md) `time_series_format`.
