# VENTING_EMITTERS

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) / 
[VENTING_EMITTERS](/about/references/keywords/VENTING_EMITTERS.md)


| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `INSTALLATIONS`      | `NAME` <br /> `EMISSION_NAME`  <br />  `CATEGORY`  <br />  `EMITTER_MODEL`    |

:::important
eCalc version 8.7: VENTING_EMITTERS keyword is introduced as a replacement for [DIRECT_EMITTERS](/about/references/keywords/DIRECT_EMITTERS.md).
eCalc version 8.6 and earlier: Use DIRECT_EMITTERS as before.
:::

## Description
The [VENTING_EMITTERS](/about/references/keywords/VENTING_EMITTERS.md) keyword covers the direct emissions on the installation
that are not consuming energy. The attributes [NAME](/about/references/keywords/NAME.md),
[EMISSION_NAME](/about/references/keywords/EMISSION_NAME.md), [CATEGORY](/about/references/keywords/CATEGORY.md) and
[EMITTER_MODEL](/about/references/keywords/EMITTER_MODEL.md) are required.

## Format
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: <emitter name>
    EMISSION_NAME: <emission name>
    CATEGORY: <category>
    EMITTER_MODEL: <emitter model>
~~~~~~~~

## Example
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: SomeVentingEmitter
    EMISSION_NAME: CH4
    CATEGORY: COLD-VENTING-FUGITIVE
    EMITTER_MODEL:
      <emitter model data>
  ...
  - NAME: SomeOtherVentingEmitter
    EMISSION_NAME: C2H6
    CATEGORY: COLD-VENTING-FUGITIVE
    EMITTER_MODEL:
      <emitter model data>
~~~~~~~~
