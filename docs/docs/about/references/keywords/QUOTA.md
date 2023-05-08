# QUOTA

[...] /
[QUOTA](QUOTA)

## Description
Quota cost in NOK/Sm<sup>3</sup> for the emission. [QUOTA](QUOTA) can either be a fixed number or an
expression (time series). With the use of an expression, a time series can be defined which can let the quota value vary over the model timespan.

## Format
~~~~~~~~yaml
QUOTA: <quota>
~~~~~~~~

## Example

~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
    FACTOR: 2.5  # kg/Sm3
    QUOTA: 240   # NOK/ton CO2
~~~~~~~~
