# VOLUME
<span className="major-change-new-feature"> 
New keyword from eCalc v8.13!
</span> 
<br></br>

[VENTING_EMITTERS](/about/references/keywords/VENTING_EMITTERS.md) /
[VOLUME](/about/references/keywords/VOLUME.md)

## Description

From eCalc 8.13: Used to define oil volume/rates and emission factors for venting emitters of [TYPE](/about/references/keywords/TYPE.md) `OIL_VOLUME`

The keywords [RATE](/about/references/keywords/RATE.md) and [EMISSIONS](/about/references/keywords/EMISSIONS.md) are required.

## Format

~~~~~~~~yaml
VOLUME:
  RATE:
    VALUE: <oil volume/rate>
    UNIT: <oil volume/rate unit>
    TYPE: <oil volume/rate type, default STREAM_DAY>
  EMISSIONS:
  - NAME: <emission name>
    EMISSION_FACTOR: <volume to emission factor, fraction of oil volume>
  ...

~~~~~~~~

## Example
~~~~~~~~yaml
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
