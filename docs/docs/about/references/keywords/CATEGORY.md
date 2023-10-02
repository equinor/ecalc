# CATEGORY
[eCalc Model](/about/references/index.md)
/ [INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) 
/ [...] / [CATEGORY](/about/references/keywords/CATEGORY.md)

| Required | Child of                                                                                                                                                                                                                                                           | Children/Options |
|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| Yes      | [CONSUMERS](/about/references/keywords/CONSUMERS.md)  <br /> [FUELCONSUMERS](/about/references/keywords/FUELCONSUMERS.md) <br /> [INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) <br /> [FUEL_TYPES](/about/references/keywords/FUEL_TYPES.md) <br /> | None             |

## Description
The [CATEGORY](/about/references/keywords/CATEGORY.md) keyword is used to specify which category certain data types belong to - these data types are:

* [CONSUMERS](/about/references/keywords/CONSUMERS.md) and [FUELCONSUMERS](/about/references/keywords/FUELCONSUMERS.md): Required
* [INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md): Optional
* [FUEL_TYPE](/about/references/keywords/FUEL_TYPES.md): Optional

Only a limited pre-defined set of categories is valid input to the 
[CATEGORY](/about/references/keywords/CATEGORY.md) keyword. The complete list of possible categories is given below. 
Please note that the input is case-sensitive. The names should be in upper-case and the spelling/dash must match the names in the list exactly.

Allowed categories for [CONSUMERS](/about/references/keywords/CONSUMERS.md) and [FUELCONSUMERS](/about/references/keywords/FUELCONSUMERS.md):

| Category                      | Description/Examples                                                                                                                                                                                                                                                                               |
|-------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ``BASE-LOAD``                 | Consumers that do not vary with production                                                                                                                                                                                                                                                         |
| ``COLD-VENTING-FUGITIVE``     | Direct emissions through cold venting and fugitive emissions                                                                                                                                                                                                                                       |
| ``COMPRESSOR``                | Gas injection compressors, export compressors, etc.                                                                                                                                                                                                                                                |
| ``FIXED-PRODUCTION-LOAD``     | Consumer that is fixed/constant when production stream is on. Note that this is simply the name of the category. eCalc™ does **not** imply any condition (that production must be > 0) when this keyword is applied. For this to occur, [CONDITION](CONDITION.md) must be used. See example below. |
| ``FLARE``                     | Flaring related energy usage/emissions                                                                                                                                                                                                                                                             |
| ``MISCELLANEOUS``             | Anything that don't apply other categories. Compressor and Genset (New in **v7.2**)                                                                                                                                                                                                                |
| ``PUMP``                      | Single speed pumps, variable speed pumps.                                                                                                                                                                                                                                                          |
| ``GAS-DRIVEN-COMPRESSOR``     | Compressor only. New in **v7.1**                                                                                                                                                                                                                                                                   |
| ``TURBINE-GENERATOR``         | Genset only. New in **v7.1**                                                                                                                                                                                                                                                                       |
| ``POWER-FROM-SHORE``          | Genset only. Dummy Genset (should have e.g. 0 fuel). New in **v7.1**                                                                                                                                                                                                                               |
| ``OFFSHORE-WIND``             | Direct load consumer only. Negative load. Indicate external power. New in **v7.1**                                                                                                                                                                                                                 |
| ``LOADING``                   | Direct load consumer only. Indicate oil volume to be loaded. New in **v8.0**                                                                                                                                                                                                                       |
| ``STORAGE``                   | Direct load consumer only. Indicate oil volume to be stored. New in **v8.0**                                                                                                                                                                                                                       |
 | ``STEAM-TURBINE-GENERATOR``   | Direct load consumer only. Negative load. Indicate power generated steam turbine. New in **v8.1**                                                                                                                                                                                                  |
| ``BOILER``                  | Genset only. Indicate steam generated. New in **v8.2**                                                                                                                                                                                                                        |
| ``HEATER``                  | Genset only. Indicate hot medium generated. New in **v8.2**                                                                                                                                                                          |

Allowed categories for [INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md):

| Category                   | Description/Examples           |
|----------------------------|--------------------------------|
| ``FIXED``                  | Fixed installation             |
| ``MOBILE``                 | Mobile/satellite installation. |

Allowed categories for [FUEL_TYPES](/about/references/keywords/FUEL_TYPES.md):

| Category                   | Description/Examples                                         |
|----------------------------|--------------------------------------------------------------|
| ``FUEL-GAS``               | Normally associated with a fixed installation                |
| ``DIESEL``                 | Normally associated with a mobile installation               |

## Format

~~~~~~~~yaml
CATEGORY: <CATEGORY>
~~~~~~~~

## Example

~~~~~~~~yaml
- NAME: name_of_my_electrical_consumer
  CATEGORY: FIXED-PRODUCTION-LOAD
  ENERGY_USAGE_MODEL:
    LOAD: 5
    CONDITION: SIM;OIL_PROD > 0
~~~~~~~~
