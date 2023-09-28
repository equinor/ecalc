# DIRECT_EMITTERS

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) / 
[DIRECT_EMITTERS](/about/references/keywords/DIRECT_EMITTERS.md)


| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `INSTALLATIONS`      | `NAME` <br /> `EMISSION_NAME`  <br />  `CATEGORY`  <br />  `EMITTER_MODEL`    |


## Description
The [DIRECT_EMITTERS](/about/references/keywords/DIRECT_EMITTERS.md) keyword covers the direct emissions on the installation
that are not consuming energy. The attributes [NAME](/about/references/keywords/NAME.md),
[EMISSION_NAME](/about/references/keywords/EMISSION_NAME.md), [CATEGORY](/about/references/keywords/CATEGORY.md) and
[EMITTER_MODEL](/about/references/keywords/EMITTER_MODEL.md) are required.

## Format
~~~~~~~~yaml
DIRECT_EMITTER:
  - NAME: <emitter name>
    EMISSION_NAME: <emission name>
    CATEGORY: <category>
    EMITTER_MODEL: <emitter model>
~~~~~~~~

## Example
~~~~~~~~yaml
DIRECT_EMITTER:
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

