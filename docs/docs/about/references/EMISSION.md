# EMISSION
<span className="major-change-new-feature"> 
New keyword from eCalc v8.8!
</span> 
<br/>

[INSTALLATIONS](/about/references/INSTALLATIONS.md) /
[VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md)

| Required   | Child of                  | Children/Options |
|------------|---------------------------|------------------|
| No         | `VENTING_EMITTERS`         | `NAME`<br/>`RATE`  |

:::important
- From eCalc version 8.8: The new keyword `EMISSION` is a part of an updated definition of [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md).
- eCalc version 8.7 and earlier: `EMISSION`-keyword cannot be used.
:::

## Description
The emission specifies the data to calculate the direct emissions on an installation. This data is used to set up
a function that may be evaluated for a set of time series and return an emission result.

The attributes [NAME](/about/references/NAME.md) and [RATE](/about/references/RATE.md) are required.

## Format
~~~~~~~~yaml
EMISSION:
  - NAME: <emission name>
    RATE:
      VALUE: <emission rate>
      UNIT: <emission rate unit, default kg/d>
      TYPE: <emission rate type, default STREAM_DAY>
~~~~~~~~

## Example
~~~~~~~~yaml
EMISSION:
  - NAME: CH4
    RATE:
      VALUE: 4
      UNIT: kg/d
      TYPE: STREAM_DAY
~~~~~~~~

