# NAME

[...] /
[NAME](/about/references/keywords/NAME.md)

## Description
Name of an entity.
[CATEGORY](/about/references/keywords/CATEGORY.md) names must be written with uppercase letters - see example below:

## Format
~~~~~~~~yaml
NAME: <name>
~~~~~~~~

## Example
Usage in [EMISSIONS](/about/references/keywords/EMISSIONS.md):

~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
~~~~~~~~

Usage in [FUEL_TYPES](/about/references/keywords/FUEL_TYPES.md) and [CATEGORIES](/about/references/keywords/CATEGORY.md):

~~~~~~~~yaml
FUEL_TYPES:
  - NAME: diesel_turbine
    CATEGORY: DIESEL
~~~~~~~~
