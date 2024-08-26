# DIRECT_EMITTERS
<span className="major-change-deprecation"> 
Deprecated from eCalc v8.7 (changed name to <strong>VENTING_EMITTERS</strong>).
</span>


[INSTALLATIONS](/about/references/INSTALLATIONS.md) / 
[DIRECT_EMITTERS](/about/references/DIRECT_EMITTERS.md)


| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `INSTALLATIONS`      | `NAME` <br /> `EMISSION_NAME`  <br />  `CATEGORY`  <br />  `EMITTER_MODEL`    |

:::important
- eCalc version 8.7: DIRECT_EMITTERS are renamed to [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md).
- eCalc version 8.6 and earlier: Use DIRECT_EMITTERS as before.
:::

## Description
The [DIRECT_EMITTERS](/about/references/DIRECT_EMITTERS.md) keyword covers the direct emissions on the installation
that are not consuming energy. The attributes [NAME](/about/references/NAME.md),
[EMISSION_NAME](/about/references/EMISSION_NAME.md), [CATEGORY](/about/references/CATEGORY.md) and
[EMITTER_MODEL](/about/references/EMITTER_MODEL.md) are required.

## Format
~~~~~~~~yaml
DIRECT_EMITTERS:
  - NAME: <emitter name>
    EMISSION_NAME: <emission name>
    CATEGORY: <category>
    EMITTER_MODEL: <emitter model>
~~~~~~~~

## Example
~~~~~~~~yaml
DIRECT_EMITTERS:
  - NAME: SomeDirectEmitter
    EMISSION_NAME: CH4
    CATEGORY: COLD-VENTING-FUGITIVE
    EMITTER_MODEL:
      <emitter model data>
  ...
  - NAME: SomeOtherDirectEmitter
    EMISSION_NAME: C2H6
    CATEGORY: COLD-VENTING-FUGITIVE
    EMITTER_MODEL:
      <emitter model data>
~~~~~~~~

