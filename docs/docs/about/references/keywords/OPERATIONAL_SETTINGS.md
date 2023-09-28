# OPERATIONAL_SETTINGS
 
[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) /
[...] /
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) / 
[OPERATIONAL_SETTINGS](/about/references/keywords/OPERATIONAL_SETTINGS.md)

## Description
Used to define the operational settings in an [ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md)
 of type `PUMP_SYSTEM` or `COMPRESSOR_SYSTEM`.

The rate [Sm<sup>3</sup>/day] through each consumer in the system may be specified in two different ways, either directly using
`RATES`, or by defining the `rate fraction<RATE_FRACTIONS>` for each consumer which is then multiplied with the
`total system rate<TOTAL_SYSTEM_RATE>`.

The suction pressure may either be specified with [SUCTION_PRESSURE](/about/references/keywords/SUCTION_PRESSURE.md)
which will then be the common suction pressure for all consumers in the system. Alternatively, 
`SUCTION_PRESSURES`  may be used to specify one suction pressure expression per consumer.

The discharge pressure may either be specified with [DISCHARGE_PRESSURE](/about/references/keywords/DISCHARGE_PRESSURE.md)
which will then be the common discharge pressure for all consumers in the system. Alternatively, 
`DISCHARGE_PRESSURES` may be used to specify one discharge pressure expression per consumer.

`CROSSOVER` may be used to specify if there are any available cross-overs between the consumers in this operational
setting.

`FLUID_DENSITIES` may be used for pump systems to specify one fluid density expression per pump.

For all keywords where there is one expression per consumer, `RATES`, `RATE_FRACTIONS`, `SUCTION_PRESSURES`,
`DISCHARGE_PRESSURES` and `FLUID_DENSITIES`, the expressions must be entered in a
list where the number of elements is equal to the number of `compressors<COMPRESSORS>`/`pumps<PUMPS>`

### RATES
A list with one expression per consumer specifying the rate [Sm<sup>3</sup>/day] for each consumer. Use either `RATES` or `RATE_FRACTIONS`,
not both in one operational setting.

### RATE_FRACTIONS
A list with one expression per consumer specifying the rate fraction for each consumer. If this is used,
[TOTAL_SYSTEM_RATE](/about/references/keywords/TOTAL_SYSTEM_RATE.md) for the [ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md)
is also required. Use either `RATES` or `RATE_FRACTIONS`, not both in one operational setting.

### SUCTION_PRESSURES
A list with one expression per consumer specifying the suction pressure for each consumer. Use either `SUCTION_PRESSURES` or 
[SUCTION_PRESSURE](/about/references/keywords/SUCTION_PRESSURE.md), not both in the same operational setting.

Use [SUCTION_PRESSURE](/about/references/keywords/SUCTION_PRESSURE.md) to set the same suction pressure for all consumers in the system and 
`SUCTION_PRESSURES` to specify one suction pressure expression per consumer.

### DISCHARGE_PRESSURES
A list with one expression per consumer specifying the discharge pressure for each consumer. Use either `DISCHARGE_PRESSURES`
or [DISCHARGE_PRESSURE](/about/references/keywords/DISCHARGE_PRESSURE.md), not both in the same operational setting.

Use [DISCHARGE_PRESSURE](/about/references/keywords/DISCHARGE_PRESSURE.md) to set the same discharge pressure for all consumers in the system and
`DISCHARGE_PRESSURES` to specify one discharge pressure expression per consumer.

### FLUID_DENSITIES
Only supported for `energy usage models<ENERGY_USAGE_MODEL>` of type `PUMP_SYSTEM`.
A list with one expression per consumer specifying the fluid density for each consumer. If used, it will over-ride
[FLUID_DENSITY](/about/references/keywords/FLUID_DENSITY.md) for the `PUMP_SYSTEM`.

Use [FLUID_DENSITY](/about/references/keywords/FLUID_DENSITY.md) for the `energy usage models<ENERGY_USAGE_MODEL>`
to set one fixed fluid density for the entire system for all operational settings. Use 
`FLUID_DENSITIES` for the `operational setting<OPERATIONAL_SETTINGS>` to vary the fluid density between consumers and operational settings.

### CROSSOVER
`CROSSOVER` specifies if rates are to be crossed over to another consumer if rate capacity is exceeded. If the
energy consumption calculation is not successful for a consumer, and the consumer has a valid cross-over defined, the
consumer will be allocated its maximum rate and the exceeding rate will be added to the cross-over consumer. To avoid
loops, a consumer can only be either receiving or giving away rate. For a cross-over to be valid, the discharge pressure
at the consumer "receiving" overshooting rate must be higher than or equal to the discharge pressure of the "sending"
consumer. This is because it is possible to choke pressure down to meet the outlet pressure in a flow line with lower
pressure, but not possible to "pressure up" in the crossover flow line.
Some examples show how the crossover logic works:

Crossover is given as and list of integer values for the first position is the first consumer, second position is the
second consumer, etc. The number specifies which consumer to send cross-over flow to, and 0 signifies no cross-over
possible. **Note that we use 1-index here.**

### Example 1:
Two consumers where there is a cross-over such that if the rate for the first consumer exceeds its capacity,
the excess rate will be processed by the second consumer. The second consumer can not cross-over to anyone.

~~~~~~~~yaml
CROSSOVER: [2, 0]
~~~~~~~~

### Example 2:
The first and second consumers may both send exceeding rate to the third consumer if their capacity is
exceeded.

~~~~~~~~yaml
CROSSOVER: [3,3,0]
~~~~~~~~

## Format
## Example
~~~~~~~~yaml
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
    - RATES:
        - SIM1;GAS_SALES
        - 0
        - SIM1;GAS_INJ
      SUCTION_PRESSURE: 50
      DISCHARGE_PRESSURES:
        - 150
        - 150
        - SIM1;INJ_PRESSURE
    - RATES:
        - SIM1;GAS_SALES {/} 2
        - SIM1;GAS_SALES {/} 2
        - SIM1;GAS_INJ
      SUCTION_PRESSURE: 50
      DISCHARGE_PRESSURES:
        - 150
        - 150
        - SIM1;INJ_PRESSURE
      CROSSOVER: [3, 3, 0]
~~~~~~~~

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP_SYSTEM
  PUMPS:
    - NAME: pump1
      CHART: water_injection_pump_reference
    - NAME: pump2
      CHART: water_injection_pump_reference
  TOTAL_SYSTEM_RATE: SIM1;WATER_INJ
  FLUID_DENSITY: (1000 {*} SIM1;WATER_PROD {+} 1050 {*} SIM2;WATER_PROD) {/} (SIM1;WATER_PROD {+} SIM2;WATER_PROD)
  OPERATIONAL_SETTINGS:
    - RATE_FRACTIONS: [1, 0]
      SUCTION_PRESSURE: 3
      DISCHARGE_PRESSURE: 200
    - RATE_FRACTIONS: [0.5, 0.5]
      SUCTION_PRESSURE: 3
      DISCHARGE_PRESSURE: 200
      FLUID_DENSITIES:
        - 1000
        - 1050
~~~~~~~~

