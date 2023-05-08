# COMPRESSOR_MODEL

[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL.md) / [COMPRESSOR_MODEL](COMPRESSOR_MODEL.md)

| Required | Child of      | Children/Options |
|----------|---------------|------------------|
| Yes      | [ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL.md)  | None             |

## Description

This keyword links the predefined [COMPRESSOR MODEL](../../modelling/setup/models/compressor_modelling/compressor_models_types/index.md) to the [COMPRESSOR ENERGY USAGE MODEL](ENERGY_USAGE_MODEL.md).

Note that this can **only** be used when a [COMPRESSOR SYSTEM](COMPRESSOR_SYSTEM.md) is used. It is possible to use the same compressor model twice in the same system - this is a common feature when there are identical compressor trains in parallel.

## Format

~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR_SYSTEM
  COMPRESSORS:
    - NAME: <name of compressor>
      COMPRESSOR_MODEL: <reference to compressor model>
      ...
~~~~~

## Example

~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR_SYSTEM
  COMPRESSORS:
    - NAME: export_compressor1
      COMPRESSOR_MODEL: export_compressor_reference
    - NAME: export_compressor2
      COMPRESSOR_MODEL: export_compressor_reference
    - NAME: injection_compressor
      COMPRESSOR_MODEL: injection_compressor_reference
~~~~~
