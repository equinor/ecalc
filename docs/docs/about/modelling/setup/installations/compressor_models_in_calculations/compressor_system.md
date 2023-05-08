---
title: Compressor system
sidebar_position: 2
description: COMPRESSOR_SYSTEM Energy Usage Model
---

# COMPRESSOR_SYSTEM energy usage model

When [COMPRESSOR_SYSTEM](../../../../references/keywords/COMPRESSOR_SYSTEM) is specified under [ENERGY_USAGE_MODEL](../../../../references/keywords/ENERGY_USAGE_MODEL) a fully defined compressor model (with charts) can be used. Here, the following are allowed under the
[COMPRESSOR_SYSTEM](../../../../references/keywords/COMPRESSOR_SYSTEM) keyword:

- [Simplified variable speed compressor train model](../../models/compressor_modelling/compressor_models_types/simplified_variable_speed_compressor_train_model),
- [Variable speed compressor train model](../../models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model) 
- [Sampled compressor model](../../facility_inputs/sampled_compressor_model)

The key difference between this model and the [COMPRESSOR](compressor) keyword is that multiple compression trains can be specified. 

## Format

~~~~~~~~yaml
NAME: <Reference name>
TYPE: COMPRESSOR
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR_SYSTEM
  CONDITION: <condition expression>
  COMPRESSORS:
    - NAME: <name of compressor>
      COMPRESSOR_MODEL: <reference to compressor model in facility inputs>
  TOTAL_SYSTEM_RATE: <expression defining the total rate in the system>
  OPERATIONAL_SETTINGS:
    <operational settings data>
~~~~~~~~

## Example

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
  TOTAL_SYSTEM_RATE: SIM1;GAS_PROD {+} SIM1;GAS_LIFT
  OPERATIONAL_SETTINGS:
    - RATES:
        - SIM1;GAS_SALES
        - 0
        - SIM1;GAS_INJ
      SUCTION_PRESSURE: 50
      DISCHARGE_PRESSURES:
        - 150
        - 150
        - SIM1;INJ_PRESSURE
    - RATES:
        - SIM1;GAS_SALES {/} 2
        - SIM1;GAS_SALES {/} 2
        - SIM1;GAS_INJ
      SUCTION_PRESSURE: 50
      DISCHARGE_PRESSURES:
        - 150
        - 150
        - SIM1;INJ_PRESSURE
~~~~~~~~
