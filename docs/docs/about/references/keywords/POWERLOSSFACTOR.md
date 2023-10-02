# POWERLOSSFACTOR

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) /
[...] /
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) /
[POWERLOSSFACTOR](/about/references/keywords/POWERLOSSFACTOR.md)

## Description
A factor that may be added to account for power line losses. E.g. if you have a subsea installation with a power line to
another installation, there may be line losses. For a power line loss of 5%, [POWERLOSSFACTOR](/about/references/keywords/POWERLOSSFACTOR.md)
is set to 0.05 and the power required from the power source (generator set) will be

$$
power_{required} = \frac{power_{subsea}}{1-POWERLOSSFACTOR}
$$

where $power_{subsea}$ is the power calculated from the energy function (before power loss is taken into account).

## Format
~~~~~~~~yaml
POWERLOSSFACTOR: <EXPRESSION>
~~~~~~~~

## Example
~~~~~~~~yaml
POWERLOSSFACTOR: 0.05
~~~~~~~~

~~~~~~~~yaml
POWERLOSSFACTOR: SIM1;POWERLOSS {+} 0.05
~~~~~~~~

