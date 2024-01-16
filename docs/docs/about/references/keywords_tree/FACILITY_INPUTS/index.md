---
sidebar_position: 2
---
# FACILITY_INPUTS
:::note
The [FACILITY_INPUTS](/about/references/keywords_tree/FACILITY_INPUTS/index.md) keyword is **mandatory** within the eCalc™ YAML file.
:::

[FACILITY_INPUTS](/about/references/keywords_tree/FACILITY_INPUTS/index.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | None                      | `ADJUSTMENT` <br />  `FILE` <br /> `HEAD_MARGIN` <br /> `TYPE`           |

## Description
`FACILITY_INPUTS` is one of six top level section keywords in eCalc™.

This part of the setup defines input files that characterize various facility elements. Each facility element is
specified in a list. These are later used as input in the [INSTALLATIONS](/about/references/keywords_tree/INSTALLATIONS/index.md) part of the setup by referencing their
[NAME](/about/references/keywords_tree/FACILITY_INPUTS/NAME.md).

All facility inputs are in essence a `CSV` (Comma separated file) file that specifies input data to a model that
calculates how much energy the equipment is using depending on the operating mode/throughput. There are multiple
supported types. The facility input type is defined using the [TYPE](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/index.md) 
keyword and defines the type of model applied to the data in this file. The input files are in `CSV` 
(Comma separated file) format. The paths to the input files may be either absolute or relative to the setup file.


See [FACILITY INPUTS](/about/modelling/setup/facility_inputs/index.md) for details about different types and their usage.