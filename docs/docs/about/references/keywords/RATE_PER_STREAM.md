# RATE_PER_STREAM

[INSTALLATIONS](INSTALLATIONS) /
[...] /
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL) / 
[RATE_PER_STREAM](RATE_PER_STREAM)

## Description
Used to define the rate for each stream for the VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL) types using a list of `expression<Expressions>`

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

