---
title: Compressor models
sidebar_position: 3
description: Using compressor models in calculations
---

# Compressor models in calculations

There are different options on how to utilise compressor models in the calculations within the 
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) section in [INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md). Three different options will be illustrated here:

No matter the compressor model type, it can either be placed in two sections, which can be:

* Under the `CONSUMERS` section under `GENERATORSETS`. This is applicable for electrical motor driven compressors where electricity is generated in de-coupled gas turbines and distributed to the individual process units.
* Under the `FUELCONSUMERS` section. Here it is necessary for the compressor model to be coupled to a gas turbine model. The coupled turbine is solely driving the compressor system to which it is attached to.

**Example**

~~~~~~~~yaml
INSTALLATIONS:
  - NAME: InstallationA
    CATEGORY: FIXED
    FUEL: fuel_gas
    GENERATORSETS:
      - NAME: gensetA
        CATEGORY: TURBINE-GENERATOR
        ELECTRICITY2FUEL: genset
        CONSUMERS:
          - NAME: Gas injection compressor
            CATEGORY: COMPRESSOR
            ENERGY_USAGE_MODEL:
              TYPE: COMPRESSOR_SYSTEM
              ...

    FUELCONSUMERS:
      - NAME: Gas export compressor
        CATEGORY: GAS-DRIVEN-COMPRESSOR 
        ENERGY_USAGE_MODEL:
          TYPE: COMPRESSOR_SYSTEM
          ...
~~~~~~~~