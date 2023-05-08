# EMITTER_MODEL

[INSTALLATIONS](INSTALLATIONS) /
[...] /
[EMITTER_MODEL](EMITTER_MODEL)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `DIRECT_EMITTERS`         | `EMISSION_RATE`  <br />  `QUOTA`   |

## Description
The emitter model specifies the data to calculate the direct emissions on an installation. This data is used to set up
a function that may be evaluated for a set of time series and return a result including the emissions emitted and
the related cost of the emissions.

The [EMISSION_RATE](EMISSION_RATE) describes the rate [kg/day] of emissions and
[QUOTA](QUOTA) specifies the cost of emission per rate of
emission [NOK/kg]. Both are required.

## Format
~~~~~~~~yaml
EMITTER_MODEL:
  - EMISSION_RATE: <emission rate [kg/day]>
    QUOTA: <emission cost per emission [NOK/kg]>
~~~~~~~~

## Example
~~~~~~~~yaml
EMITTER_MODEL:
  - EMISSION_RATE: 4  # [kg/day]
    QUOTA: 10  # [NOK/kg]
~~~~~~~~

