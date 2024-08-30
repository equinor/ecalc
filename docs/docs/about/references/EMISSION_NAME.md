# EMISSION_NAME
<span className="major-change-deprecation"> 
Deprecated from eCalc v8.8 (is included in <strong>EMISSION</strong>).
</span> 
<br></br>

[...] /
[EMISSION_NAME](/about/references/EMISSION_NAME.md)

| Required   | Child of                                            | Children/Options                   |
|------------|-----------------------------------------------------|------------------------------------|
| Yes         | `VENTING_EMITTERS` | None                               |

:::important
- eCalc version 8.8: [EMISSION_NAME](/about/references/EMITTER_MODEL.md) is deprecated, instead NAME is given in [EMISSION](/about/references/EMISSION.md).
- eCalc version 8.7: [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md) keyword is replacing the [DIRECT_EMITTERS](/about/references/DIRECT_EMITTERS.md) keyword.
- eCalc version 8.6 and earlier: Use DIRECT_EMITTERS as before.
:::

## Description
Name of an entity.

## Format
~~~~~~~~yaml
EMISSION_NAME: <name>
~~~~~~~~

## Example
Usage in [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md):

~~~~~~~~yaml
VENTING_EMITTERS:
  - EMISSION_NAME: CH4
~~~~~~~~

