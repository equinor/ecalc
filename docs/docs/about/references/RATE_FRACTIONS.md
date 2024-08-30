# RATE_FRACTIONS

## Description

A list with one expression per consumer specifying the rate fraction for each consumer. If this is used, `TOTAL_SYSTEM_RATE` for the `ENERGY_USAGE_MODEL` is also required. You can use either `RATES` or `RATE_FRACTIONS`; however, not both in one operational setting.

When specifying the rate fraction, the first fraction will relate to the first operational unit mentioned - i.e. if a pump system has two pumps, the first pump mentioned will relate to the rate fraction.

Note that in the case of a compressor, the same method is utilised for specifying rate fractions.

## Format

~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP_SYSTEM
  PUMPS:
    - NAME: <pump name>
      CHART: <chart reference>
    - NAME: <pump name>
      CHART: <chart reference>
  TOTAL_SYSTEM_RATE: <system rate>
  FLUID_DENSITY: <fluid density>
  OPERATIONAL_SETTINGS:
    - RATE_FRACTIONS: <[fraction 1, fraction 2]>
      ...
    - RATE_FRACTIONS:  <[fraction 1, fraction 2]>
      ...
~~~~

## Example

~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP_SYSTEM
  PUMPS:
    - NAME: pump1
      CHART: water_injection_pump_reference
    - NAME: pump2
      CHART: water_injection_pump_reference
  TOTAL_SYSTEM_RATE: SIM1;WATER_INJ
  FLUID_DENSITY: 1030
  OPERATIONAL_SETTINGS:
    - RATE_FRACTIONS: [1, 0]
      SUCTION_PRESSURE: 3
      DISCHARGE_PRESSURE: 200
    - RATE_FRACTIONS: [0.5, 0.5]
      SUCTION_PRESSURE: 3
      DISCHARGE_PRESSURE: 200
      FLUID_DENSITIES:
        - 1000
        - 1050
~~~~