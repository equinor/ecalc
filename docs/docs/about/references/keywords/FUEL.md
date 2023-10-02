# FUEL

... /
[FUEL](/about/references/keywords/FUEL.md)

## Description

The [FUEL](/about/references/keywords/FUEL.md) keyword defines the fuel type that can be used in
`INSTALLATIONS`, `GENERATORSETS`, or `FUELCONSUMERS`.
It can be set directly and used for the entire time interval, or it can be set differently for different time intervals.

### Format

~~~~~~~~yaml
FUEL: <fuel_type>
~~~~~~~~

or

~~~~~~~~yaml
FUEL:
  <DATE>: <fuel_type>
  <DATE>: <fuel_type>
~~~~~~~~

### Example

#### Constant fuel type

~~~~~~~~yaml
FUEL: fuel_gas
~~~~~~~~

#### Time-varying fuel type

This example assumes that two fuels have been defined: `fuel_gas` and `diesel`.

~~~~~~~~yaml
FUEL:
  1994-01-01: fuel_gas
  2000-01-01: diesel
~~~~~~~~
