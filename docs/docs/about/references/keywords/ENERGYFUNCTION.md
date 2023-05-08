# ENERGYFUNCTION
 
[INSTALLATIONS](INSTALLATIONS) /
[...] / 
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL) / 
[ENERGYFUNCTION](ENERGYFUNCTION)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `ENERGY_USAGE_MODEL`         | `None`   |

## Description

This refers to an energy function model defined in either [FACILITY INPUTS](FACILITY_INPUTS.md) or in [MODELS](MODELS.md) used for [ENERGY USAGE MODEL](ENERGY_USAGE_MODEL.md).
The following atrributes can be utilised:

* [COMPRESSOR MODEL](../../modelling/setup/installations/compressor_models_in_calculations/index.md)
* [PUMP ENERGY USAGE MODEL](../../modelling/setup/installations/pump_models_in_calculations)
* [TABULATED ENERGY USAGE MODEL](ENERGY_USAGE_MODEL.md)

## Format

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: <energy usage model type>
  ENERGYFUNCTION: <reference to energy function in facility inputs or models of compressor type>
~~~~~~~~

## Example

~~~~~~~~yaml

FACILITY_INPUTS:
  - NAME: compressor_model_reference
    TYPE: COMPRESSOR_TABULAR
    FILE: <file path>

...

INSTALLATIONS:
  - NAME: InstallationA
    CATEGORY: FIXED
    FUEL: fuel_gas
    GENERATORSETS:
      - NAME: gensetA
        CATEGORY: TURBINE-GENERATOR
        ELECTRICITY2FUEL: genset
        CONSUMERS:
         - NAME: compressor
            CATEGORY: COMPRESSOR
            ENERGY_USAGE_MODEL:
              TYPE: COMPRESSOR
              ENERGYFUNCTION: compressor_model_reference
              ...

    FUELCONSUMERS:
      - NAME: compressor
        CATEGORY: GAS-DRIVEN-COMPRESSOR 
        ENERGY_USAGE_MODEL:
          TYPE: COMPRESSOR
          ENERGYFUNCTION: compressor_model_reference
          ...

~~~~~~~~
