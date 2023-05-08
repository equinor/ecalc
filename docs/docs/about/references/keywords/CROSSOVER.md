# CROSSOVER

[INSTALLATIONS](INSTALLATIONS) /
[...] / [ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL.md) / 
[OPERATIONAL_SETTINGS](OPERATIONAL_SETTINGS.md) / [CROSSOVER](COMPRESSOR_MODEL.md)

| Required | Child of      | Children/Options |
|----------|---------------|------------------|
| Yes      | [OPERATIONAL_SETTINGS](OPERATIONAL_SETTINGS.md)  | None             |

## Description

`CROSSOVER` specifies what rates will be crossed over from one consumer to another if rate capacity is exceed.
If the energy consumption calculation is not successful for a consumer, and the consumer has a valid cross-over defined, the consumer will be allocated its maximum rate and the exceeding rate will be added to the cross-over consumer.
To avoid loops, a consumer can only be either receiving or giving away rate. For a cross-over to be valid, the discharge pressure at the consumer "receiving" overshooting rate must be higher than or equal to the discharge pressure of the "sending" consumer. This is because it is possible to choke pressure down to meet the outlet pressure in a flow line with lower pressure, but not possible to "pressure up" in the crossover flow line. Some examples show how the crossover logic works:

Crossover is given as and list of integer values for the first position is the first consumer, second position is the second consumer, etc. The number specifies which consumer to send cross-over flow to, and 0 signifies no cross-over possible. Note that we use 1-index here.

## Example

~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR_SYSTEM
  COMPRESSORS:
    - NAME: export_compressor1
      COMPRESSOR_MODEL: export_compressor_reference
    - NAME: export_compressor2
      COMPRESSOR_MODEL: export_compressor_reference
    - NAME: injection_compressor
      COMPRESSOR_MODEL: injection_compressor_reference
  TOTAL_SYSTEM_RATE: SIM1;GAS_PROD {+} SIM1;GAS_LIFT
  OPERATIONAL_SETTINGS:
      ...
      CROSSOVER: [3, 3, 0]
~~~~
