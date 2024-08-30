# FUELCONSUMERS

[INSTALLATIONS](/about/references/INSTALLATIONS.md) / 
[FUELCONSUMERS](/about/references/FUELCONSUMERS.md)

## Description
The [FUELCONSUMERS](/about/references/FUELCONSUMERS.md) keyword covers the fuel consumers on the installation
that are not generators. The attributes [NAME](/about/references/NAME.md), 
[ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) and 
[CATEGORY](/about/references/CATEGORY.md) are required, while 
[FUEL](/about/references/FUEL.md) is optional and may be used to
override the installation's default fuel type.

## Format
~~~~~~~~yaml
FUELCONSUMERS:
  - NAME: <consumer name>
    CATEGORY: <category>
    ENERGY_USAGE_MODEL: <energy usage model>
    FUEL: <fuel specification>
~~~~~~~~

## Example
~~~~~~~~yaml
FUELCONSUMERS:
  - NAME: CompressorFuelConsumer
    CATEGORY: GAS-DRIVEN-COMPRESSOR
    ENERGY_USAGE_MODEL:
      <energy usage model data>
  - NAME: FlareFuelConsumer
    CATEGORY: FLARE
    ENERGY_USAGE_MODEL:
      <energy usage model data>
  ...
  - NAME: SomeOtherFuelConsumer
    CATEGORY: MISCELLANEOUS
    FUEL: fuel_gas
    ENERGY_USAGE_MODEL:
      <energy usage model data>
~~~~~~~~

