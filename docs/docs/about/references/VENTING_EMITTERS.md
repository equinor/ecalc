# VENTING_EMITTERS

<span className="major-change-new-feature"> 
New definition of VENTING_EMITTERS from eCalc v8.13!
</span> 
<br></br>

[INSTALLATIONS](/about/references/INSTALLATIONS.md) / 
[VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md)


| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `INSTALLATIONS`      | `NAME` <br /> `EMISSION_NAME`  <br />  `CATEGORY`  <br />  `EMITTER_MODEL`   <br />  `EMISSIONS`  <br />  `VOLUME` |

:::important
- eCalc version 8.13: Updated definition of `VENTING_EMITTERS`. New mandatory keyword [TYPE](/about/references/TYPE.md) is defining the venting emitter type. Based on the selected type, the new keywords [EMISSIONS](/about/references/EMISSIONS.md) (`TYPE`: `DIRECT_EMISSION`) or [VOLUME](/about/references/VOLUME.md) (`TYPE`: `OIL_VOLUME`) should be specified.
- eCalc version 8.8: Updated definition of `VENTING_EMITTERS`. New keyword [EMISSION](/about/references/EMISSION.md) is replacing [EMITTER_MODEL](/about/references/EMITTER_MODEL.md) and [EMISSION_NAME](/about/references/EMISSION_NAME.md). Now possible to define `UNIT` and `TYPE` for emission rate.  
- eCalc version 8.7: [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md) keyword is replacing the [DIRECT_EMITTERS](/about/references/DIRECT_EMITTERS.md) keyword.
- eCalc version 8.6 and earlier: Use `DIRECT_EMITTERS` as before.
:::


## eCalc version 8.7 and before: Description
The [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md) keyword covers the direct emissions on the installation
that are not consuming energy. The attributes [NAME](/about/references/NAME.md),
[EMISSION_NAME](/about/references/EMISSION_NAME.md), [CATEGORY](/about/references/CATEGORY.md) and
[EMITTER_MODEL](/about/references/EMITTER_MODEL.md) are required.

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

## eCalc from version 8.8: Description
The attributes [NAME](/about/references/NAME.md), [CATEGORY](/about/references/CATEGORY.md) and
[EMISSION](/about/references/EMISSION.md) are required.

## Format
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: <emitter name>
    CATEGORY: <category>
    EMISSION:
      <emission data>

~~~~~~~~

## Example
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: SomeVentingEmitter
    CATEGORY: COLD-VENTING-FUGITIVE
    EMISSION:
      <emission data>
  ...
  - NAME: SomeOtherVentingEmitter
    CATEGORY: COLD-VENTING-FUGITIVE
    EMISSION:
      <emission data>
~~~~~~~~

## eCalc from version 8.13: Description
The keywords [NAME](/about/references/NAME.md), [CATEGORY](/about/references/CATEGORY.md) and [TYPE](/about/references/TYPE.md) are required. The venting emitter type can be either `DIRECT_EMISSION` or `OIL_VOLUME`.

The keywords [EMISSIONS](/about/references/EMISSIONS.md) or [VOLUME](/about/references/VOLUME.md) are required, dependent on which venting emitter type is used. 

Venting emitter of [TYPE](/about/references/TYPE.md) `DIRECT_EMISSION`: Specify emission rates directly.

## Format
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: <emitter name>
    CATEGORY: <category>
    TYPE: DIRECT_EMISSION
    EMISSIONS:
      <emission data>

~~~~~~~~

## Example
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: SomeVentingEmitter
    CATEGORY: COLD-VENTING-FUGITIVE
    TYPE: DIRECT_EMISSION
    EMISSIONS:
      - NAME: co2
        RATE:
          VALUE: 4
          UNIT: KG_PER_DAY
          TYPE: STREAM_DAY
      - NAME: ch4
        RATE:
          VALUE: 2
          UNIT: KG_PER_DAY
          TYPE: STREAM_DAY
~~~~~~~~

Venting emitter of [TYPE](/about/references/TYPE.md) `OIL_VOLUME`: Specify oil loading/storage volumes, and emission factors - to calculate emissions as fractions of the volume.

## Format
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: <emitter name>
    CATEGORY: <category>
    TYPE: OIL_VOLUME
    VOLUME:
      <oil volumes/rates and emission factors>

~~~~~~~~

## Example
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: SomeVentingEmitter
    CATEGORY: COLD-VENTING-FUGITIVE
    TYPE: OIL_VOLUME
    VOLUME:
      RATE:
        VALUE: 10
        UNIT: SM3_PER_DAY
        TYPE: STREAM_DAY
      EMISSIONS:
      - NAME: co2
        EMISSION_FACTOR: 0.04
      - NAME: ch4
        EMISSION_FACTOR: 0.02
~~~~~~~~
