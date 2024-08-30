# GENERATORSETS

[INSTALLATIONS](/about/references/INSTALLATIONS.md) / 
[GENERATORSETS](/about/references/GENERATORSETS.md)

## Description
Under [GENERATORSETS](/about/references/GENERATORSETS.md) one or
several `generator sets` (a 'set' of an engine of some sort and a generator) are specified in a list.
Each generator set requires three sub-keywords, [ELECTRICITY2FUEL](/about/references/ELECTRICITY2FUEL.md) and 
[CONSUMERS](/about/references/CONSUMERS.md) and [CATEGORY](/about/references/CATEGORY.md). Optional keywords are [CABLE_LOSS](/about/references/CABLE_LOSS.md) and [MAX_USAGE_FROM_SHORE](/about/references/MAX_USAGE_FROM_SHORE.md), only relevant if [CATEGORY](/about/references/CATEGORY.md) is `POWER-FROM-SHORE`. 

This keyword is optional. However, the only requirement is that each
installation must have at least one of [GENERATORSETS](/about/references/GENERATORSETS.md)
and [FUELCONSUMERS](/about/references/FUELCONSUMERS.md).

See [GENERATOR SETS](/about/modelling/setup/installations/generator_sets_in_calculations.md) for more details about usage.