# PUMPS

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) / [...] /
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) / 
[PUMPS](/about/references/keywords/PUMPS.md)

## Description
Used to define a list of pumps in a `PUMP_SYSTEM ENERGY USAGE MODEL`. Each pump is defined with a name and with a 
`facility input<FACILITY_INPUTS>` reference to a pump type energy function.

## Format
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP_SYSTEM
  PUMPS:
    - NAME: <name of compressor>
      CHART: <reference to pump model in facility inputs>
~~~~~~~~

## Example 1
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP_SYSTEM
  PUMPS:
    - NAME: pump1
      CHART: water_injection_pump_reference
    - NAME: pump2
      CHART: water_injection_pump_reference
~~~~~~~~

## Example 2 (Detailed)
~~~~~~~~yaml
- NAME: waterinjection
  CATEGORY: PUMP
  ENERGY_USAGE_MODEL:
    2019-01-01:
      TYPE: PUMP_SYSTEM
      PUMPS:
        - NAME: pump_a
          CHART: winj_pumpchart_PA03A
        - NAME: pump_b
          CHART: winj_pumpchart_PA03B
        - NAME: pump_c
          CHART: winj_pumpchart_PA03C
        - NAME: pump_d
          CHART: winj_pumpchart_PA03D
        - NAME: pump_e
          CHART: winj_pumpchart_PA03E
      TOTAL_SYSTEM_RATE: SIM8;WATER_INJ
      FLUID_DENSITY: 1030
      OPERATIONAL_SETTINGS:
        - RATE_FRACTIONS: [1, 0, 0, 0, 0]
          SUCTION_PRESSURE: 14
          DISCHARGE_PRESSURE: 250
        - RATE_FRACTIONS: [0.5, 0.5, 0, 0, 0]
          SUCTION_PRESSURE: 14
          DISCHARGE_PRESSURE: 250
        - RATE_FRACTIONS: [0.33, 0.33, 0.34, 0, 0]
          SUCTION_PRESSURE: 14
          DISCHARGE_PRESSURE: 250
        - RATE_FRACTIONS: [0.25, 0.25, 0.25, 0.25, 0]
          SUCTION_PRESSURE: 14
          DISCHARGE_PRESSURE: 250
        - RATE_FRACTIONS: [0.2, 0.2, 0.2, 0.2, 0.2]
          SUCTION_PRESSURE: 14
          DISCHARGE_PRESSURE: 250
~~~~~~~~

