# COMPRESSORS

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) / 
[...] /
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) / 
[COMPRESSOR_SYSTEM](/about/references/keywords/COMPRESSOR_SYSTEM.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `ENERGY_USAGE_MODEL`      | None                               |

## Description
Used to define a list of compressors in a compressor system model (

[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) of type `COMPRESSOR_SYSTEM`).
Each compressor is defined with a name and a reference to a compressor energy function defined in either
[FACILITY_INPUTS](/about/references/keywords/FACILITY_INPUTS.md) or [MODELS](/about/references/keywords/MODELS.md)

## Format
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR_SYSTEM
  COMPRESSORS:
    - NAME: <name of compressor>
      COMPRESSOR_MODEL: <reference to compressor model in facility inputs>
  TOTAL_SYSTEM_RATE: <optional total system rate [Sm3/day]>
  OPERATIONAL_SETTINGS: <operational settings>
~~~~~~~~

See [OPERATIONAL_SETTINGS](/about/references/keywords/OPERATIONAL_SETTINGS.md) for details.

## Example 1
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR_SYSTEM
  COMPRESSORS:
    - NAME: export_compressor1
      COMPRESSOR_MODEL: export_compressor_reference
    - NAME: export_compressor2
      COMPRESSOR_MODEL: export_compressor_reference
    - NAME: injection_compressor
      COMPRESSOR_MODEL: injection_compressor_reference
~~~~~~~~

## Example 2 (Detailed)

:::note
When adding a “DATE” the next line is indented.
:::
~~~~~~~~yaml
- NAME: gassys27
  CATEGORY: COMPRESSOR
  ENERGY_USAGE_MODEL:
    2020-04-01:
      TYPE: COMPRESSOR_SYSTEM
      COMPRESSORS:
        - NAME: gassys27a
          COMPRESSOR_MODEL: gas3da
        - NAME: gassys27b
          COMPRESSOR_MODEL: gas3db
      TOTAL_SYSTEM_RATE: SIM8;GAS_PROD  # [Sm3/day]
      OPERATIONAL_SETTINGS:
        - RATE_FRACTIONS: [1, 0]
          SUCTION_PRESSURE: 50
          DISCHARGE_PRESSURE: 155
        - RATE_FRACTIONS: [0.5, 0.5]
          SUCTION_PRESSURE: 50
          DISCHARGE_PRESSURE: 155
~~~~~~~~
