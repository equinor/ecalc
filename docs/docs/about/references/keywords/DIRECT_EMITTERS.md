# DIRECT_EMITTERS

[INSTALLATIONS](INSTALLATIONS) / 
[DIRECT_EMITTERS](DIRECT_EMITTERS)


| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `INSTALLATIONS`      | `NAME` <br /> `EMISSION_NAME`  <br />  `CATEGORY`  <br />  `EMITTER_MODEL`    |


## Description
The [DIRECT_EMITTERS](DIRECT_EMITTERS) keyword covers the direct emissions on the installation
that are not consuming energy. The attributes [NAME](NAME),
[EMISSION_NAME](EMISSION_NAME), [CATEGORY](CATEGORY) and
[EMITTER_MODEL](EMITTER_MODEL) are required.

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

