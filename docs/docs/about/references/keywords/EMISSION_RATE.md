# EMISSION_RATE
 
[INSTALLATIONS](INSTALLATIONS) /
[...] /
[EMITTER_MODEL](EMITTER_MODEL) /
[EMISSION_RATE](EMISSION_RATE)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes         | `EMITTER_MODEL`      | None                               |

## Description
Used to define the emission rate for some [EMITTER_MODEL](EMITTER_MODEL) types
using an [Expressions](EXPRESSION)

## Format
~~~~~~~~yaml
EMISSION_RATE: <emission rate [kg/day] expression or time series>
~~~~~~~~

## Example
~~~~~~~~yaml
EMISSION_RATE: 10.0  # [kg/day]
~~~~~~~~

