# CONSUMERS

[INSTALLATIONS](INSTALLATIONS) / 
[GENERATORSETS](GENERATORSETS.md) / 
[CONSUMERS](CONSUMERS)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `GENERATORSETS`           | `CATEGORY`    <br />  `NAME`     <br />    `ENERGY_USAGE_MODEL`    |

## Description
Consumers getting electrical power from the generator set. The attributes [NAME](NAME), 
[CATEGORY](CATEGORY) and [ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL)
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

