# EMISSION_RATE
<span className="major-change-deprecation"> 
Deprecated from eCalc v8.8 (is included in <strong>EMISSION</strong>).
</span> 
<br></br>

[INSTALLATIONS](/about/references/INSTALLATIONS.md) /
[...] /
[EMITTER_MODEL](/about/references/EMITTER_MODEL.md) /
[EMISSION_RATE](/about/references/EMISSION_RATE.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes         | `EMITTER_MODEL`      | None                               |

## Description
Used to define the emission rate for some [EMITTER_MODEL](/about/references/EMITTER_MODEL.md) types
using an [Expressions](/about/references/EXPRESSION.md)

## Format
~~~~~~~~yaml
EMISSION_RATE: <emission rate [kg/day] expression or time series>
~~~~~~~~

## Example
~~~~~~~~yaml
EMISSION_RATE: 10.0  # [kg/day]
~~~~~~~~

