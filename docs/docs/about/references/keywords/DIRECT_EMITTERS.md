# DIRECT_EMITTERS

> Deprecated since eCalc v8.7 (changed name to `VENTING_EMITTERS`)

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) / 
[DIRECT_EMITTERS](/about/references/keywords/DIRECT_EMITTERS.md)


| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `INSTALLATIONS`      | `NAME` <br /> `EMISSION_NAME`  <br />  `CATEGORY`  <br />  `EMITTER_MODEL`    |

:::important
eCalc version 8.7: DIRECT_EMITTERS are renamed to [VENTING_EMITTERS](/about/references/keywords/VENTING_EMITTERS.md).
eCalc version 8.6 and earlier: Use DIRECT_EMITTERS as before.
:::

## Description
The [DIRECT_EMITTERS](/about/references/keywords/DIRECT_EMITTERS.md) keyword covers the direct emissions on the installation
that are not consuming energy. The attributes [NAME](/about/references/keywords/NAME.md),
[EMISSION_NAME](/about/references/keywords/EMISSION_NAME.md), [CATEGORY](/about/references/keywords/CATEGORY.md) and
[EMITTER_MODEL](/about/references/keywords/EMITTER_MODEL.md) are required.

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

