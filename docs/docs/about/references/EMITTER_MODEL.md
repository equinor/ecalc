# EMITTER_MODEL
<span className="major-change-deprecation"> 
Deprecated from eCalc v8.8 (replaced by <strong>EMISSION</strong>).
</span>
<br></br>

[INSTALLATIONS](/about/references/INSTALLATIONS.md) /
[...] /
[EMITTER_MODEL](/about/references/EMITTER_MODEL.md)

| Required   | Child of                  | Children/Options  |
|------------|---------------------------|-------------------|
| No         | `VENTING_EMITTERS`         | `EMISSION_RATE`   |

:::important
- eCalc version 8.8: [EMITTER_MODEL](/about/references/EMITTER_MODEL.md) is deprecated, and replaced by new [EMISSION](/about/references/EMISSION.md) keyword.
- eCalc version 8.7: [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md) keyword is replacing the [DIRECT_EMITTERS](/about/references/DIRECT_EMITTERS.md) keyword.
- eCalc version 8.6 and earlier: Use DIRECT_EMITTERS as before.
:::

## Description
The emitter model specifies the data to calculate the direct emissions on an installation. This data is used to set up
a function that may be evaluated for a set of time series and return an emission result.

The [EMISSION_RATE](/about/references/EMISSION_RATE.md) describes the rate [kg/day] of emissions, and is required.

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

