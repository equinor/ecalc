# FUELCONSUMERS

[INSTALLATIONS](INSTALLATIONS) / 
[FUELCONSUMERS](FUELCONSUMERS.md)

## Description
The [FUELCONSUMERS](FUELCONSUMERS.md) keyword covers the fuel consumers on the installation
that are not generators. The attributes [NAME](NAME), 
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL) and 
[CATEGORY](CATEGORY) are required, while 
[FUEL](FUEL) is optional and may be used to
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

