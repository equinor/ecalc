# EMITTER_MODEL

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) /
[...] /
[EMITTER_MODEL](/about/references/keywords/EMITTER_MODEL.md)

| Required   | Child of                  | Children/Options  |
|------------|---------------------------|-------------------|
| No         | `VENTING_EMITTERS`         | `EMISSION_RATE`   |

:::important
- eCalc version 8.7: [VENTING_EMITTERS](/about/references/keywords/VENTING_EMITTERS.md) keyword is replacing the [DIRECT_EMITTERS](/about/references/keywords/DIRECT_EMITTERS.md) keyword.
- eCalc version 8.6 and earlier: Use DIRECT_EMITTERS as before.
:::

## Description
The emitter model specifies the data to calculate the direct emissions on an installation. This data is used to set up
a function that may be evaluated for a set of time series and return a result including the emissions emitted and
the related cost of the emissions.

The [EMISSION_RATE](/about/references/keywords/EMISSION_RATE.md) describes the rate [kg/day] of emissions, and is required.

## Format
~~~~~~~~yaml
EMITTER_MODEL:
  - EMISSION_RATE: <emission rate [kg/day]>
~~~~~~~~

## Example
~~~~~~~~yaml
EMITTER_MODEL:
  - EMISSION_RATE: 4  # [kg/day]
~~~~~~~~

