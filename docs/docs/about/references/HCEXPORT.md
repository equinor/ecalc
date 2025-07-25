# HCEXPORT

[INSTALLATIONS](/about/references/INSTALLATIONS.md) /
[HCEXPORT](/about/references/HCEXPORT.md)

## Description
[HCEXPORT](/about/references/HCEXPORT.md) defines the export of hydrocarbons as a number of oil equivalents in Sm<sup>3</sup>.
This keyword is required for the output of emission intensity (i.e., kg CO<sub>2</sub>/boe). 

**Note:**
CO₂ intensity (kg CO₂/boe) expresses emissions per unit of hydrocarbon exported. If only prognosis data is used, 
the reported value shows the "remaining lifetime intensity". To obtain the true lifetime intensity, historical data 
must also be included (this calculation must be done outside eCalc).

`HCEXPORT` could be a single time series variable or an `expression <expressions>` containing multiple time series variables.
Typically it would be the sum of exported oil and gas in units of oil equivalents.

:::info What is hydrocarbon export?
Hydrocarbon export is the oil equivalents of what is exported for sale and only these volumes should
be included here. I.e., it is important to distinguish between *produced gas* and *sales gas*.
:::
## Format
~~~~~~~~yaml
HCEXPORT: <EXPRESSION>  # [Sm3/day]
~~~~~~~~

or

~~~~~~~~yaml
HCEXPORT:
 <DATE>: <EXPRESSION>  # [Sm3/day]
 <DATE>: <EXPRESSION>  # [Sm3/day]
~~~~~~~~

## Example
### Basic usage
~~~~~~~~yaml
HCEXPORT: SIM;OIL_PROD {+} SIM;GAS_SALES {/} 1000
~~~~~~~~

### With time dependency
In this example the gas export starts later than production start up:

~~~~~~~~yaml
HCEXPORT:
  2001-01-01: SIM1;OIL_PROD
  2005-01-01: SIM2:OIL_PROD {+} SIM1;GAS_SALES {/} 1000
~~~~~~~~

### Full example
Example showing [HCEXPORT](/about/references/HCEXPORT.md) the modelling hierarchy:

~~~~~~~~yaml
INSTALLATIONS:
  - NAME: installation_A
    FUEL: fuel_gas
    HCEXPORT: SIM;OIL_PROD:FIELD_A {+} SIM;GAS_SALES:FIELD_A {/} 1000
    GENERATORSETS:
      <Data for the generator sets to be put her>
    FUELCONSUMERS:
      <Data for the fuel consumers to be put here>
  - NAME: installation_B
    HCEXPORT: SIM;OIL_PROD:FIELD_B {+} SIM;GAS_SALES:FIELD_B{/} 1000
    GENERATORSETS:
      <Data for the generator sets to be put her>
    FUELCONSUMERS:
      <Data for the fuel consumers to be put here>
~~~~~~~~

