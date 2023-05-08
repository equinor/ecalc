# NAME

[...] /
[NAME](NAME)

## Description
Name of an entity.
[CATEGORY](CATEGORY.md) names must be written with uppercase letters - see example below:

## Format
~~~~~~~~yaml
NAME: <name>
~~~~~~~~

## Example
Usage in [EMISSIONS](EMISSIONS.md):

~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
~~~~~~~~

Usage in [FUEL_TYPES](FUEL_TYPES.md) and [CATEGORIES](CATEGORY.md):

~~~~~~~~yaml
FUEL_TYPES:
  - NAME: diesel_turbine
    CATEGORY: DIESEL
~~~~~~~~
