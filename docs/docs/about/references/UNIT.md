# UNIT

## Description

`UNIT` is a keyword that can be specified for:
- [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md) - [EMISSIONS](/about/references/EMISSIONS.md) - [RATE](/about/references/RATE.md) or
- [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md) - [VOLUME](/about/references/VOLUME.md) - [RATE](/about/references/RATE.md)

## Format
Venting emitter of [TYPE](/about/references/TYPE.md) `DIRECT_EMISSION`:
~~~~yaml
RATE:
  VALUE: <emission rate>
  UNIT: <emission rate unit, KG_PER_DAY (default), TONS_PER_DAY are supported units>
  TYPE: <emission rate type, default STREAM_DAY>
~~~~

Venting emitter of [TYPE](/about/references/TYPE.md) `OIL_VOLUME`: 
~~~~yaml
RATE:
  VALUE: <emission rate>
  UNIT: <emission rate unit, SM3_PER_DAY is only supported unit>
  TYPE: <emission rate type, default STREAM_DAY>
~~~~

## Example 
TYPE: DIRECT_EMISSION
~~~~yaml
RATE:
  VALUE: 2
  UNIT: KG_PER_DAY
  TYPE: STREAM_DAY
~~~~
