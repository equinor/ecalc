# NAME

[...] /
[NAME](/about/references/NAME.md)

## Description
Name of an entity.
[CATEGORY](/about/references/CATEGORY.md) names must be written with uppercase letters - see example below:

## Format
~~~~~~~~yaml
NAME: <name>
~~~~~~~~

## Example
Usage in [EMISSIONS](/about/references/EMISSIONS.md):

~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
~~~~~~~~

Usage in [FUEL_TYPES](/about/references/FUEL_TYPES.md) and [CATEGORIES](/about/references/CATEGORY.md):

~~~~~~~~yaml
FUEL_TYPES:
  - NAME: diesel_turbine
    CATEGORY: DIESEL
~~~~~~~~
