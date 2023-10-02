---
title: Tabular models
sidebar_position: 4
description: Tabular models
---

Additional equipment that are considered to be energy consumers can be specified using the keyword `TABULAR`. 
This is given that a form of reservoir rates (oil/gas production) can be linked to either fuel or power consumption. 

This is considered to be a consumer energy function for pure barycentric interpolation, no extrapolation outside
convex area. One column defines the function value, the rest of the columns defines the
variables for a 1D (if one variable column) or multidimensional interpolation.

## Header and unit requirements

| Header | Unit| Comment |
| ----- | ----| --- |
| Power | MW | For power driven consumers|
| Fuel  | Sm<sup>3</sup>/day| For fuel (turbine) driven consumers|

Variable headers can be chosen freely as long as these correspond to the defined variables for the function.

### Example
#### 1D tabular energy function
Contents of the file `energyfunc_1d_rate_fuel.csv`:

~~~~~~~~text
RATE,     FUEL
0,        0
1,        137750
1000000,  137750
2000000,  145579
3000000,  153335
4000000,  161022
5000000,  168644
~~~~~~~~

The entry in [FACILITY_INPUTS](/about/references/keywords/FACILITY_INPUTS.md):

~~~~~~~~yaml
FACILITY_INPUTS:
  - NAME: gasinjectiondata
    FILE: energyfunc_1d_rate_fuel.csv
    TYPE: TABULAR
~~~~~~~~

The entry in [INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) under a fuel consumer:

~~~~~~~~yaml
INSTALLATIONS:
  ....
    - NAME: gasinjection
      CATEGORY: COMPRESSOR
      ENERGY_USAGE_MODEL:
        TYPE: TABULATED
        ENERGYFUNCTION: gasinjectiondata
        VARIABLES:
          - NAME: RATE
            EXPRESSION: SIM1;GAS_INJ  # [Sm3/day]
~~~~~~~~

:::note Note
Note that the name `RATE` in the input file (under [FACILITY_INPUT](/about/modelling/setup/facility_inputs/index.md)) and the variable name `RATE` under [VARIABLES](/about/references/keywords/VARIABLES.md)
 must be equal!
:::

#### 3D tabular energy function
Contents of file `energyfunc_3d_rate_ps_pd_power.csv`:

~~~~~~~~text
     RATE, SUCTION_PRESSURE, DISCHARGE_PRESSURE,       POWER
# [Sm3/d],            [bar],              [bar],        [MW]
 1.00E+06,               10,              12.72,      0.3664
 1.00E+06,               10,              26.21,       2.293
 1.00E+06,               26,              31.36,      0.2739
 1.00E+06,               26,              70.77,        6.28
 1.00E+06,               34,              41.21,       0.368
 1.00E+06,               34,              94.24,       8.435
 1.00E+06,               78,              94.12,      0.7401
 1.00E+06,               78,              231.6,       22.46
 6.00E+06,               26,              36.93,       4.197
 6.00E+06,               26,              57.43,       7.32
 6.00E+06,               38,              46.96,       2.156
 6.00E+06,               38,              106.2,       9.557
 6.00E+06,               54,              67.26,        1.95
 6.00E+06,               54,              155.6,       14.35
 6.00E+06,               78,              94.17,       1.399
 6.00E+06,               78,              231.6,       22.46
 1.10E+07,               42,              66.92,       9.712
 1.10E+07,               42,              81.63,       11.89
 1.10E+07,               62,              75.64,       3.678
 1.10E+07,               62,              180.8,       16.94
 1.10E+07,               78,              97.79,       3.452
 1.10E+07,               78,              231.6,       22.46
~~~~~~~~

The entry in [FACILITY_INPUTS](/about/references/keywords/FACILITY_INPUTS.md):

~~~~~~~~yaml
FACILITY_INPUTS:
  - NAME: booster
    FILE: energyfunc_3d_rate_ps_pd_power.csv
    TYPE: TABULAR
~~~~~~~~

The entry in [INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) under a fuel consumer (for 3-d tabular):

~~~~~~~~yaml
INSTALLATIONS:
  ...
    - NAME: gasexport
      CATEGORY: COMPRESSOR
      ENERGY_USAGE_MODEL:
        TYPE: TABULATED
        ENERGYFUNCTION: booster
        VARIABLES:
          - NAME: RATE
            EXPRESSION: SIM1;GAS_SALES  # [Sm3/day]
          - NAME: SUCTION_PRESSURE
            EXPRESSION: SIM1;SUCTION_PRESSURE {+} 3  # [bara]
          - NAME: DISCHARGE_PRESSURE
            EXPRESSION: 100  # [bara]
~~~~~~~~