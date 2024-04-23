# GENERATORSETS

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) / 
[GENERATORSETS](/about/references/keywords/GENERATORSETS.md)

## Description
Under [GENERATORSETS](/about/references/keywords/GENERATORSETS.md) one or
several `generator sets` (a 'set' of an engine of some sort and a generator) are specified in a list.
Each generator set requires three sub-keywords, [ELECTRICITY2FUEL](/about/references/keywords/ELECTRICITY2FUEL.md) and 
[CONSUMERS](/about/references/keywords/CONSUMERS.md) and [CATEGORY](/about/references/keywords/CATEGORY.md). Optional keywords are [CABLE_LOSS](/about/references/keywords/CABLE_LOSS.md) and [MAX_USAGE_FROM_SHORE](/about/references/keywords/MAX_USAGE_FROM_SHORE.md), only relevant if [CATEGORY](/about/references/keywords/CATEGORY.md) is `POWER-FROM-SHORE`. 

This keyword is optional. However, the only requirement is that each
installation must have at least one of [GENERATORSETS](/about/references/keywords/GENERATORSETS.md)
and [FUELCONSUMERS](/about/references/keywords/FUELCONSUMERS.md).

See [GENERATOR SETS](/about/modelling/setup/installations/generator_sets_in_calculations.md) for more details about usage.