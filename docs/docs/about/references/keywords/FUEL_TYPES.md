# FUEL_TYPES

[FUEL_TYPES](FUEL_TYPES)

## Description
This part of the setup specifies the various fuel types and associated emissions
used in the model. Each fuel type is specified in a list and the defined fuels can later be referred to the 
[INSTALLATIONS](INSTALLATIONS) part of the setup by its name.

A fuel type can have a fuel-cost [PRICE](PRICE) associated with
its use. The use of fuel can lead to one or more emission types, specified in [EMISSIONS](EMISSIONS.md),
which in turn can have associated costs.
You can optionally specify a [CATEGORY](CATEGORY).

See [FUEL TYPES](docs/about/modelling/setup/fuel_types) for more details about usage.