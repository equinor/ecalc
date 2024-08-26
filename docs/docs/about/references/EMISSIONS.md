# EMISSIONS
 
[FUEL_TYPES](/about/references/FUEL_TYPES.md) / 
[EMISSIONS](/about/references/EMISSIONS.md)
or
[VENTING_EMITTERS](/about/references/FUEL_TYPES.md) /
[EMISSIONS](/about/references/EMISSIONS.md)
or 
[VENTING_EMITTERS](/about/references/FUEL_TYPES.md) /
[VOLUME](/about/references/VOLUME.md) /
[EMISSIONS](/about/references/EMISSIONS.md)



| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `FUEL_TYPES`         | `FACTOR`  <br />  `NAME`            |


## Description
This can be used in three ways:

- In [EMISSIONS](/about/references/EMISSIONS.md) one or more emissions related to the use of fuel is specified as
a list. Each emission entry is **required** to have a [NAME](/about/references/NAME.md) and a [FACTOR](/about/references/FACTOR.mdx).
- [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md) of type DIRECT_EMISSION: To specify emission rates directly.
- [VENTING_EMITTERS](/about/references/VENTING_EMITTERS.md) of type OIL_VOLUME: To specify emission factors, i.e. calculate emissions as fractions of oil loading/storage volumes.

## For fuels
### Format
~~~~~~~~yaml
EMISSIONS:
  - NAME: <name>
    FACTOR: <factor>
~~~~~~~~

### Example
For example, if you want to add CO<sub>2</sub> emissions associated to the usage of a [FUEL_TYPES](/about/references/FUEL_TYPES.md)
you write the following:

~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
    FACTOR: 2.5  # [kg/Sm3]
~~~~~~~~

## For venting emitters (type: DIRECT_EMISSION, from eCalc v8.13)
Note that the emission name is case-insensitive.
The keywords [NAME](/about/references/NAME.md) and [RATE](/about/references/RATE.md) are required.

### Format
~~~~~~~~yaml
EMISSIONS:
  - NAME: <name>
    RATE: <emission rate>
  ...
~~~~~~~~

### Example
~~~~~~~~yaml
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
## For venting emitters (type: OIL_VOLUME, from eCalc v8.13)
Note that the emission name is case-insensitive.
The keywords [NAME](/about/references/NAME.md) and `EMISSION_FACTOR` are required.

### Format
~~~~~~~~yaml
EMISSIONS:
  - NAME: <name>
    EMISSION_FACTOR: <volume to emission factor>
  ...
~~~~~~~~

### Example
~~~~~~~~yaml
EMISSIONS:
  - NAME: co2
    EMISSION_FACTOR: 0.04
  - NAME: ch4
    EMISSION_FACTOR: 0.02
~~~~~~~~