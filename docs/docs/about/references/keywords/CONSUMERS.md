# CONSUMERS

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) / 
[GENERATORSETS](/about/references/keywords/GENERATORSETS.md) / 
[CONSUMERS](/about/references/keywords/CONSUMERS.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `GENERATORSETS`           | `CATEGORY`    <br />  `NAME`     <br />    `ENERGY_USAGE_MODEL`    |

## Description
Consumers getting electrical power from the generator set. The attributes [NAME](/about/references/keywords/NAME.md), 
[CATEGORY](/about/references/keywords/CATEGORY.md) and [ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md)
are all required

## Format
~~~~~~~~yaml
CONSUMERS:
  - NAME: <consumer name>
    CATEGORY: <category>
    ENERGY_USAGE_MODEL: <energy usage model>
~~~~~~~~

## Example
~~~~~~~~yaml
CONSUMERS:
  - NAME: SomeElectricalConsumer
    CATEGORY: COMPRESSOR
    ENERGY_USAGE_MODEL:
      <energy usage model data>
  - NAME: SomeOtherElectricalConsumer
    CATEGORY: BASE-LOAD
    ENERGY_USAGE_MODEL:
      <energy usage model data>
  ...
  - NAME: ElectricalConsumerN
    CATEGORY: MISCELLANEOUS
    ENERGY_USAGE_MODEL:
      <energy usage model data>
~~~~~~~~

