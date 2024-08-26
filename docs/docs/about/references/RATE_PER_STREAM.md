# RATE_PER_STREAM

[INSTALLATIONS](/about/references/INSTALLATIONS.md) /
[...] /
[ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) / 
[RATE_PER_STREAM](/about/references/RATE_PER_STREAM.md)

## Description
Used to define the rate for each stream for the VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
[ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) types using a list of `expression<Expressions>`

## Format
~~~~~~~~yaml
RATE_PER_STREAM:
    - <rate expression>
    - <rate expression>
~~~~~~~~

## Example
~~~~~~~~yaml
RATE_PER_STREAM:
    - SIM1:GAS_PROD
    - SIM1:GAS_SALES
~~~~~~~~

