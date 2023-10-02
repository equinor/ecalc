# ELECTRICITY2FUEL

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) / 
[GENERATORSETS](/about/references/keywords/GENERATORSETS.md) / 
[ELECTRICITY2FUEL](/about/references/keywords/ELECTRICITY2FUEL.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes         | `GENERATORSETS`      | None                               |

## Description
[ELECTRICITY2FUEL](/about/references/keywords/ELECTRICITY2FUEL.md) specifies the correlation between the electric power
delivered and the fuel consumed by a generator set.


:::note
Note that this describes the relation for a *set* of generators and if there is more than one
generator, the power vs. fuel usually makes a "jump" when the capacity of the generator(s) is
exceeded and an additional generator is started.
:::

[ELECTRICITY2FUEL](/about/references/keywords/ELECTRICITY2FUEL.md) may be modelled with a constant function through time or
with different power vs. fuel relations for different time intervals.

## Format
~~~~~~~~yaml
ELECTRICITY2FUEL: <facility_input_reference>
~~~~~~~~

or

~~~~~~~~yaml
ELECTRICITY2FUEL:
  <DATE>: <facility_input_reference_1>
  <DATE>: <facility_input_reference_2>
~~~~~~~~

## Example
### Example 1
~~~~~~~~yaml
ELECTRICITY2FUEL: generatorset_electricity_to_fuel_reference
~~~~~~~~

### Example 2
~~~~~~~~yaml
ELECTRICITY2FUEL:
  2001-01-01: generatorset_electricity_to_fuel_reference1
  2005-01-01: generatorset_electricity_to_fuel_reference2
~~~~~~~~

Where `generatorset_electricity_to_fuel_reference<N>` is a [FACILITY_INPUTS](/about/references/keywords/FACILITY_INPUTS.md)
 of [TYPE](/about/references/keywords/TYPE.md) `ELECTRICITY2FUEL`.
