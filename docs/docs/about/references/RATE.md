# RATE

[INSTALLATIONS](/about/references/INSTALLATIONS.md) /
[...] /
[ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) / 
[RATE](/about/references/RATE.md)

## Description

This can be used in three ways:

- Used to define the rate for some [ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md)
types using an `Expression`
- Used defining the units of a [PUMP](/about/modelling/setup/facility_inputs/pump_modelling/pump_charts.md) and [COMPRESSOR CHARTS](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md).
- From eCalc v8.8: Used to define the rate for [EMISSION](/about/references/EMISSION.md) in [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md)

## Format

~~~~~~~~yaml
RATE: <rate expression>
~~~~~~~~

~~~~~~~~yaml
    - NAME: <model name>
      TYPE: <pump or compressor type>
      ...
      UNITS:
        RATE: <AM3_PER_HOUR>
        ...
~~~~~~~~

## Example
~~~~~~~~yaml
RATE: SIM1:GAS_PROD
~~~~~~~~

~~~~~~~~yaml
    - NAME: pump
      TYPE: PUMP_CHART_VARIABLE_SPEED
      ...
      UNITS:
        RATE: <AM3_PER_HOUR>
        ...
~~~~~~~~

## Use in EMISSIONS or VOLUME for VENTING_EMITTERS (from eCalc v8.8)
The keywords `VALUE` and [CATEGORY](/about/references/CATEGORY.md) are required, while [UNIT](/about/references/UNIT.md) and [TYPE](/about/references/TYPE.md) are optional. 

**New feature in eCalc version 9.16**:The optional keyword [CONDITION](/about/references/CONDITION.md) and [CONDITIONS](/about/references/CONDITIONS.md) can be used to define conditions that affect the `RATE`.

For venting emitters of `TYPE` `DIRECT_EMISSION` (from eCalc v8.13):
`RATE` is specified under [EMISSIONS](/about/references/EMISSIONS.md). Allowed values for `UNIT` are KG_PER_DAY and TONS_PER_DAY, while STREAM_DAY and CALENDAR_DAY are valid for `TYPE`.

For venting emitters of `TYPE` `OIL_VOLUME` (from eCalc v8.13):
`RATE` is specified under [VOLUME](/about/references/VOLUME.md). Only allowed value for `UNIT` is SM3_PER_DAY

Example with venting emitter of `TYPE` `DIRECT_EMISSION`:
### Format
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: <emitter name>
    CATEGORY: <category>
    TYPE: <emission type>
    EMISSIONS:
      - NAME: <emission name>
        RATE:
          VALUE: <emission rate>
          UNIT: <emission rate unit, default KG_PER_DAY>
          TYPE: <emission rate type, default STREAM_DAY>
          CONDITION: <condition expression>
~~~~~~~~


### Example

~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: SomeVentingEmitter
    CATEGORY: COLD-VENTING-FUGITIVE
    TYPE: DIRECT_EMISSION
    EMISSIONS:
      - NAME: CH4
        RATE:
          VALUE: 4
          UNIT: KG_PER_DAY
          TYPE: STREAM_DAY
          CONDITION: DRILLING;PRODUCTION_DAYS == 1
~~~~~~~~

Example with venting emitter of `TYPE` `OIL_VOLUME`:
### Example
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
        CONDITION: DRILLING;PRODUCTION_DAYS == 1
      EMISSIONS:
      - NAME: co2
        EMISSION_FACTOR: 0.04
      - NAME: ch4
        EMISSION_FACTOR: 0.02
~~~~~~~~