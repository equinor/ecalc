---
sidebar_position: 2
---
# FACTOR

[FUEL_TYPES](/about/references/keywords_tree/FUEL_TYPES/index.md) /
[EMISSIONS](/about/references/keywords_tree/FUEL_TYPES/EMISSIONS/index.md) /
[FACTOR](/about/references/keywords_tree/FUEL_TYPES/EMISSIONS/FACTOR.md)

## Description
`FACTOR` is a single value (kg/Sm<sup>3</sup>) used to define the emissions in kg per Sm<sup>3</sup>
of the fuel gas used on the installation. That is, how many kilograms of e.g. CO<sub>2</sub> are emitted per 
Sm<sup>3</sup> of fuel gas burnt.

Say your fuel emits 2.5 kg CO<sub>2</sub> per Sm<sup>3</sup> of burned fuel, you can model this like

~~~~~~~~yaml
FUEL_TYPES:
  - NAME: my_fuel
    EMISSIONS:
      - NAME: CO2
        FACTOR: 2.5  # [kg/Sm3]
~~~~~~~~