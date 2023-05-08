# RATE

[INSTALLATIONS](INSTALLATIONS) /
[...] /
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL) / 
[RATE](RATE)

## Description

This can be used in two ways:

- Used to define the rate for some [ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL)
types using an `Expression`
- Used defining the units of a [PUMP](../../modelling/setup/facility_inputs/pump_modelling/pump_charts) and [COMPRESSOR CHARTS](../../modelling/setup/models/compressor_modelling/compressor_charts/).

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
