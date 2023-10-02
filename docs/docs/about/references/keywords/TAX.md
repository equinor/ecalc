# TAX

[FUEL_TYPES](/about/references/keywords/FUEL_TYPES.md) / 
[EMISSIONS](/about/references/keywords/EMISSIONS.md) / 
[TAX](/about/references/keywords/TAX.md)

## Description
Tax is payable in NOK/Sm<sup>3</sup> for the emission. [TAX](/about/references/keywords/TAX.md) can either be a fixed number or an 
`expression <Expressions>`.

## Format
~~~~~~~~yaml
EMISSIONS:
  - NAME: <name>
    FACTOR: <factor>
    TAX: <tax>
~~~~~~~~

## Example
### Fixed tax
~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
    FACTOR: 2.5  # [kg/Sm3]
    TAX: 1.5 # [NOK/Sm3]
~~~~~~~~

### Variable tax
By making use of `Expressions`, you can model a varying tax price through time:

~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
    FACTOR: 2.5 # [kg/Sm3]
    TAX: TAX_FILENAME;TAX
    QUOTA: 240 # [NOK/ton]
~~~~~~~~

where the file `TAX_FILENAME.csv` could have the following content:

~~~~~~~~yaml
DATE,           TAX
01.01.2017,     1.5
01.01.2018,     1.6
01.01.2019,     1.7
01.01.2020,     1.8
01.01.2021,     1.9
01.01.2022,     2.0
01.01.2023,     2.1
~~~~~~~~

Make sure the file [TYPE](/about/references/keywords/TYPE.md) is set to `EMISSION_TAX_PER_FUEL_VOLUME` to have a default `RIGHT`
[INTERPOLATION_TYPE](/about/references/keywords/INTERPOLATION_TYPE.md).
