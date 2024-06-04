# RATE

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) /
[...] /
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) / 
[RATE](/about/references/keywords/RATE.md)

## Description

This can be used in three ways:

- Used to define the rate for some [ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md)
types using an `Expression`
- Used defining the units of a [PUMP](/about/modelling/setup/facility_inputs/pump_modelling/pump_charts.md) and [COMPRESSOR CHARTS](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md).
- From eCalc v8.8: Used to define the rate for [EMISSION](/about/references/keywords/EMISSION.md) in [VENTING_EMITTERS](/about/references/keywords/VENTING_EMITTERS.md)

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

## Use in EMISSION for VENTING_EMITTERS (from eCalc v8.8)
The keywords `VALUE` and [CATEGORY](/about/references/keywords/CATEGORY.md) are required, while [UNIT](/about/references/keywords/UNIT.md) and [TYPE](/about/references/keywords/TYPE.md) are optional. 

For venting emitters of `TYPE` `DIRECT_EMISSION`:
Allowed values for `UNIT` are KG_PER_DAY and TONS_PER_DAY, while STREAM_DAY and CALENDAR_DAY are valid for `TYPE`.

For venting emitters of `TYPE` `OIL_VOLUME`:
Only allowed value for `UNIT` is SM3_PER_DAY

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
~~~~~~~~