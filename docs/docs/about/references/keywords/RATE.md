# RATE

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) /
[...] /
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) / 
[RATE](/about/references/keywords/RATE.md)

## Description

This can be used in two ways:

- Used to define the rate for some [ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md)
types using an `Expression`
- Used defining the units of a [PUMP](/about/modelling/setup/facility_inputs/pump_modelling/pump_charts.md) and [COMPRESSOR CHARTS](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md).

## Format

~~~~~~~~yaml
RATE: <rate expression>
~~~~~~~~

~~~~~~~~yaml
    - NAME: <model name>
      TYPE: <pump or compressor type>
      ...
      UNITS:
        RATE: <AM3_PER_HOUR>
        ...
~~~~~~~~

## Example
~~~~~~~~yaml
RATE: SIM1:GAS_PROD
~~~~~~~~

~~~~~~~~yaml
    - NAME: pump
      TYPE: PUMP_CHART_VARIABLE_SPEED
      ...
      UNITS:
        RATE: <AM3_PER_HOUR>
        ...
~~~~~~~~
