---
sidebar_position: 1
title: Simple model
description: A simple model with a single installation
---
# Simple model example
The following is an example with one installation called `Installation A` that exports oil (`OIL_PROD`) and gas (`GAS_PROD`).
The installation emits CO<sub>2</sub> that is subject to taxation and emission quotas.

On this installation, the following components are identified:

```mermaid
graph TD;
   A(Installation A) --> B(Flare);
   A --> C(Gas export compressor);
   A --> D(Generator set A);
   D --> E(Base production load);
   D --> F(Gas injection compressor);
   D --> G(Produced water reinjection pump);
   D --> H(Sea water injection pump);
   style A stroke:red;
   style E stroke:blue;
   style F stroke:blue;
   style G stroke:blue;
   style H stroke:blue;
```

The results of a performed characterization of the equipment are listed below:

| Consumer                         |Type                | Description                                                                                                                                              |
|----------------------------------|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Generator set A                  |Generator set       | Variable fuel consumer with electricity to fuel function                                                                                                 |
| Base production load             |Power consumer      | Constant load 11.8 MW                                                                                                                                    |
| Gas injection compressor         |Power consumer      | Variable consumption depending on gas injection rate and lift gas rate                                                                                   |
| Produced water reinjection pump |Power consumer      | Variable consumption depending on water production rate and water injection rate. The pump suction pressure is 10 bar and discharge pressure is 200 bar. |
| Sea water injection pump         |Power consumer      | Variable consumption depending on a complex combination on water injection rate and water production rate                                                |
| Flare                            |Direct fuel consumer| Before 1.1.2005: Constant fuel rate 10000 Sm<sup>3</sup>/day, From 1.1.2005: Constant fuel rate 7000 Sm<sup>3</sup>/day                                                        |
| Gas export compressor            |Direct fuel consumer| Variable fuel consumer depending on gas sales rate                                                                                                       |

## YAML model overview
The YAML model consist of these main components:
- Time series inputs - [TIME_SERIES](../../references/keywords/TIME_SERIES.md)
- Facility characterization input - [FACILITY_INPUTS](../../references/keywords/FACILITY_INPUTS)
- Fuel input - [FUEL_TYPES](../../references/keywords/FUEL_TYPES)
- Model variables - [VARIABLES](../../references/keywords/VARIABLES)
- Installation topology - [INSTALLATIONS](../../references/keywords/INSTALLATIONS)

The YAML setup file looks like this:

~~~~~~~~yaml title="model.yaml"
TIME_SERIES:
  <placeholder>
FACILITY_INPUTS:
  <placeholder>
FUEL_TYPES:
  <placeholder>
VARIABLES:
  <placeholder>
INSTALLATIONS:
  <placeholder>
~~~~~~~~

We will now replace the placeholders for each of the main keywords above.

## TIME_SERIES
The reservoir variables, in this case, are found in a CSV (Comma separated file) `production_data.csv`.
We give the time-series data a name that can be referenced as variables elsewhere in the form `<NAME>:<NAME OF COLUMN>`.
See [TIME_SERIES](../../references/keywords/TIME_SERIES.md) for further details.

~~~~~~~~yaml title="model.yaml"
TIME_SERIES:
  - NAME: SIM
    FILE: production_data.csv
    TYPE: DEFAULT
~~~~~~~~

## FACILITY_INPUTS
We specify CSV input data for processing equipment using FACILITY_INPUTS. This is used for generatorsets,
tabulated/sampled models and pump charts.
See [FACILITY_INPUTS](../../references/keywords/FACILITY_INPUTS.md) for further details.

Here we define a tabulated genset, a sampled compressor, a sampled compressor driven by a turbine, a sampled pump,
and a single speed pump chart. These will be used in the final model for illustration.
Note that more complicated energy models are defined under the [MODELS-keyword](../../references/keywords/MODELS.md).

See the input data further down to understand the input formats.

~~~~~~~~yaml title="model.yaml"
FACILITY_INPUTS:
  - NAME: genset
    FILE: genset.csv
    TYPE: ELECTRICITY2FUEL
  - NAME: compressor_sampled
    FILE: compressor_sampled.csv
    TYPE: COMPRESSOR_TABULAR
  - NAME: compressor_with_turbine_sampled
    FILE: compressor_sampled_with_turbine.csv
    TYPE: COMPRESSOR_TABULAR
  - NAME: pump_sampled
    FILE: pump_sampled.csv
    TYPE: TABULAR
  - NAME: pump_chart
    FILE: pump_chart.csv
    TYPE: PUMP_CHART_SINGLE_SPEED
    UNITS:
      HEAD: M
      RATE: AM3_PER_HOUR
      EFFICIENCY: PERCENTAGE
~~~~~~~~

## FUEL_TYPES
In this example there is only one [FUEL_TYPES](../../references/keywords/FUEL_TYPES) - `fuel_gas`. This has a price/value
of 1.5 NOK/Sm<sup>3</sup> and the emissions we model with the fuel is CO<sub>2</sub>. The CO<sub>2</sub> factor
is 2.19 kg CO2 per Sm<sup>3</sup> fuel gas burned. The CO<sub>2</sub> tax is set to 1.5 NOK/Sm<sup>3</sup>
fuel gas burned, and it has a quota price of 260 NOK/ton.

~~~~~~~~yaml title="model.yaml"
FUEL_TYPES:
  - NAME: fuel_gas
    PRICE: 1.5  #NOK/Sm3
    EMISSIONS:
      - NAME: CO2
        FACTOR: 2.19 #CO2/Sm3 fuel gas burned
        TAX: 1.5 #NOK/Sm3 fuel gas burned
        QUOTA: 260 #NOK/ton
~~~~~~~~

## VARIABLES
To run the model it is recommended to specify [VARIABLES](../../references/keywords/VARIABLES),
instead of hard coding values in difference places. This makes it easier to develop, maintain and understand the model
by allowing descriptive variable names and avoid duplications.

For our model, we specify the following variables:

~~~~~~~~yaml title="model.yaml"
VARIABLES:
  hydrocarbon_export_sm3_per_day:
    VALUE: SIM;OIL_PROD {+} SIM;GAS_PROD {/} 1000  # divide the gas rate by 1000 to get oil equivalent
  sea_water_injection_rate_m3_per_day:
    VALUE: SIM;WATER_INJ {-} SIM;WATER_PROD {+} SIM;WATER_PROD {*} (SIM;WATER_PROD < 1500) {+} (SIM;WATER_PROD {-} 17000) {*} (SIM;WATER_PROD > 17000) {*} (SIM;WATER_PROD < 18500)
  gas_export_rate_sm3_per_day:
    VALUE: SIM;GAS_PROD
  gas_injection_rate_sm3_per_day:
    VALUE: SIM;GAS_INJ {+} SIM;GAS_LIFT
  produced_water_reinjection_condition:
    VALUE: SIM;WATER_PROD > 1500
  produced_water_reinjection_total_system_rate_m3_per_day:
    VALUE: SIM;WATER_PROD
  flare_fuel_rate_sm3_day:
    1995-10-01:
      VALUE: 10000
    2005-01-01:
      VALUE: 7000
~~~~~~~~

We reference the [TIME_SERIES](#time_series) `SIM` using the column names from the CSV file. Here we use for example
`SIM:OIL_PROD` (Field Oil Production Rate) `SIM:GAS_PROD` (Field Gas Sales Rate).

:::tip
It is possible to specify if-else conditions by multiplying with boolean values.
This has been done in the $var.salt_water_injection_rate_m3_per_day variable example above.
:::

## INSTALLATION

An installation is composed of hydrocarbon export, a default fuel for that installation and consumers in the form
of generatorsets (with electric sub-consumers), and direct fuel consumers.

We specify:
- `NAME`: the installation name
- `HCEXPORT`: Hydrocarbon export in Sm<sup>3</sup>/day by referring to the variable specified under [VARIABLES](#variables) above.
- `FUEl`: Default fuel specified in [FUEL_TYPES](#fuel_types) above.

~~~~~~~~yaml
INSTALLATIONS:
  - NAME: Installation A
    HCEXPORT: $var.hydrocarbon_export_sm3_per_day
    FUEL: fuel_gas
    GENERATORSETS:
      <placeholder>
    FUELCONSUMERS:
      <placeholder>
~~~~~~~~

### GENERATORSETS
There is one generator set, `Generator set A`. This has a power to fuel function defined in
[FACILITY_INPUTS](#facility_inputs) with the name `genset`. Further, the consumers getting
power from the generator set are *Base production load*, *Gas injection compressor*, *Produced water re-injection pump*
and *Sea-water injection pump*. The setup for `Generator set A` thus becomes:

~~~~~~~~yaml
    GENERATORSETS:
      - NAME: Generator set A
        ELECTRICITY2FUEL: genset
        CATEGORY: TURBINE-GENERATOR
        CONSUMERS:
          - NAME: Base production load
            CATEGORY: BASE-LOAD
            ENERGY_USAGE_MODEL:
              <placeholder>
          - NAME: Gas injection compressor
            CATEGORY: COMPRESSOR
            ENERGY_USAGE_MODEL:
              <placeholder>
          - NAME: Produced water reinjection pump
            CATEGORY: PUMP
            ENERGY_USAGE_MODEL:
              <placeholder>
          - NAME: Sea water injection pump
            CATEGORY: PUMP
            ENERGY_USAGE_MODEL:
              <placeholder>
~~~~~~~~

### FUELCONSUMERS
The direct fuel consumers are **Flare** and **Gas export compressor**.
~~~~~~~~yaml title="model.yaml"
    FUELCONSUMERS:
      - NAME: Flare
        CATEGORY: FLARE
        ENERGY_USAGE_MODEL:
          <placeholder>
      - NAME: Gas export compressor
        CATEGORY: COMPRESSOR
        ENERGY_USAGE_MODEL:
          <placeholder>
~~~~~~~~

## ENERGY_USAGE_MODEL
We will now fill in the final placeholders with detailed [ENERGY_USAGE_MODEL](../../references/keywords/ENERGY_USAGE_MODEL.md)s.


`Base production load` has a constant load of 11.8 MW:

~~~~~~~~yaml
          - NAME: Base production load
            CATEGORY: BASE-LOAD
            ENERGY_USAGE_MODEL:
              TYPE: DIRECT
              LOAD: 11.8 # MW
~~~~~~~~

`Gas injection compressor` is represented by a tabulated (sampled) energy usage model defining the relationship
between the gas injection rate [Sm<sup>3</sup>/day] and the corresponding power requirement. The gas rate is already defined
in the variable [gas_injection_rate_sm3_per_day](#variables) as `SIM;GAS_INJ {+} SIM;GAS_LIFT`:
~~~~~~~~yaml
          - NAME: Gas injection compressor
            CATEGORY: COMPRESSOR
            ENERGY_USAGE_MODEL:
              TYPE: COMPRESSOR
              ENERGYFUNCTION: compressor_sampled
              RATE: $var.gas_injection_rate_sm3_per_day
              SUCTION_PRESSURE: 50 #not used but a number is needed for eCalc
              DISCHARGE_PRESSURE: 200 #not used but a number is needed for eCalc
~~~~~~~~

`Produced water reinjection pump` is variable and its energy function is dependent on the field's water
production rate (`WATER_PROD`) that is set in the variable [produced_water_reinjection_condition](#variables) as `SIM;WATER_PROD`.
The pump only runs when the variables [produced_water_reinjection_condition](#variables) evaluates to true as `SIM;WATER_PROD > 1500`.
This is when the water production is above 1500 Sm3/day. Fluid density, suction pressure and discharge pressure
is also defined:
~~~~~~~~yaml
          - NAME: Produced water reinjection pump
            CATEGORY: PUMP
            ENERGY_USAGE_MODEL:
              TYPE: PUMP
              CONDITION: $var.produced_water_reinjection_condition
              ENERGYFUNCTION: pump_chart
              RATE: $var.produced_water_reinjection_total_system_rate_m3_per_day
              FLUID_DENSITY: 1010
              SUCTION_PRESSURE: 10  # [bara]
              DISCHARGE_PRESSURE: 200  # [bara]
~~~~~~~~

`Sea water injection pump` has an energy function that is dependent on the seawater injection rate.
This rate is not modeled explicitly in the reservoir input source, but it may be computed
from the injection (`WATER_INJ`) and production (`WATER_PROD`) rate by the following rules:

- In general, the seawater injection rate (`SEAWATER_INJ`), is the difference between injected and
  produced water: `SEAWATER_INJ = WATER_INJ - WATER_PROD`.

- When the produced water rate is below 1500 SM3/day, this goes directly to sea, such that
  `SEAWATER_INJ = WATER_INJ` when `WATER_PROD < 1500`.

- When the produced water rate is between 17000 and 18500 SM3/day, everything above 17000 SM3/day
  goes directly to the sea, thus `SEAWATER_INJ = WATER_INJ - 17000` when `17000 < WATER_PROD < 18500`.

This is specified as the variable [sea_water_injection_rate_m3_per_day](#variables) above and is defined as:

The model is specified:
~~~~~~~~yaml
          - NAME: Sea water injection pump
            CATEGORY: PUMP
            ENERGY_USAGE_MODEL:
              TYPE: TABULATED
              ENERGYFUNCTION: pump_sampled
              VARIABLES:
                - NAME: RATE
                  EXPRESSION: $var.sea_water_injection_rate_m3_per_day
~~~~~~~~

The flare is changing on the 1st of January 2005. Therefore, we need to use a different constant
fuel consumption value before and after this date. This is done using the variable [flare_fuel_rate_sm3_day](#variables)
above.

The model is specified:
~~~~~~~~yaml
      - NAME: Flare
        CATEGORY: FLARE
        ENERGY_USAGE_MODEL:
          TYPE: DIRECT
          FUELRATE: $var.flare_fuel_rate_sm3_day
~~~~~~~~

Gasexport is a variable fuel consumer whose energy function depends on the field gas sales rate (`GAS_PROD`) defined
in the variable [gas_export_rate_sm3_per_day](#variables) as `SIM;GAS_PROD`. Even though it is not used in the eCalc model, suction and discharge pressure needs to be specified in order for the model to run. 

The model is specified:
~~~~~~~~yaml
      - NAME: Gas export compressor
        CATEGORY: COMPRESSOR
        ENERGY_USAGE_MODEL:
          TYPE: COMPRESSOR
          ENERGYFUNCTION: compressor_with_turbine_sampled
          RATE: $var.gas_export_rate_sm3_per_day
          SUCTION_PRESSURE: 50 #not used but a number is needed for eCalc
          DISCHARGE_PRESSURE: 200 #not used but a number is needed for eCalc
~~~~~~~~

## Full eCalc YAML model
~~~~~~~~yaml title="model.yaml"
TIME_SERIES:
  - NAME: SIM
    FILE: production_data.csv
    TYPE: DEFAULT
FACILITY_INPUTS:
  - NAME: genset
    FILE: genset.csv
    TYPE: ELECTRICITY2FUEL
  - NAME: compressor_sampled
    FILE: compressor_sampled.csv
    TYPE: COMPRESSOR_TABULAR
  - NAME: compressor_with_turbine_sampled
    FILE: compressor_sampled_with_turbine.csv
    TYPE: COMPRESSOR_TABULAR
  - NAME: pump_sampled
    FILE: pump_sampled.csv
    TYPE: TABULAR
  - NAME: pump_chart
    FILE: pump_chart.csv
    TYPE: PUMP_CHART_SINGLE_SPEED
    UNITS:
      HEAD: M
      RATE: AM3_PER_HOUR
      EFFICIENCY: PERCENTAGE

FUEL_TYPES:
  - NAME: fuel_gas
    PRICE: 1.5  # NOK/Sm3
    EMISSIONS:
      - NAME: CO2
        FACTOR: 2.19  # CO2/Sm3 fuel gas burned
        TAX: 1.5  # NOK/Sm3 fuel gas burned
        QUOTA: 260  # NOK/ton

VARIABLES:
  hydrocarbon_export_sm3_per_day:
    VALUE: SIM;OIL_PROD {+} SIM;GAS_PROD {/} 1000  # divide the gas rate by 1000 to get oil equivalent
  sea_water_injection_rate_m3_per_day:
    VALUE: SIM;WATER_INJ {-} SIM;WATER_PROD {+} SIM;WATER_PROD {*} (SIM;WATER_PROD < 1500) {+} (SIM;WATER_PROD {-} 17000) {*} (SIM;WATER_PROD > 17000) {*} (SIM;WATER_PROD < 18500)
  gas_export_rate_sm3_per_day:
    VALUE: SIM;GAS_PROD
  gas_injection_rate_sm3_per_day:
    VALUE: SIM;GAS_INJ {+} SIM;GAS_LIFT
  produced_water_reinjection_condition:
    VALUE: SIM;WATER_PROD > 1500
  produced_water_reinjection_total_system_rate_m3_per_day:
    VALUE: SIM;WATER_PROD
  flare_fuel_rate_sm3_day:
    1995-10-01:
      VALUE: 10000
    2005-01-01:
      VALUE: 7000

INSTALLATIONS:
  - NAME: Installation A
    HCEXPORT: $var.hydrocarbon_export_sm3_per_day
    FUEL: fuel_gas
    GENERATORSETS:
      - NAME: Generator set A
        ELECTRICITY2FUEL: genset
        CATEGORY: TURBINE-GENERATOR
        CONSUMERS:
          - NAME: Base production load
            CATEGORY: BASE-LOAD
            ENERGY_USAGE_MODEL:
              TYPE: DIRECT
              LOAD: 11.8 # MW
          - NAME: Gas injection compressor
            CATEGORY: COMPRESSOR
            ENERGY_USAGE_MODEL:
              TYPE: COMPRESSOR
              ENERGYFUNCTION: compressor_sampled
              RATE: $var.gas_injection_rate_sm3_per_day
              SUCTION_PRESSURE: 50 #not used but a number is needed for eCalc
              DISCHARGE_PRESSURE: 200 #not used but a number is needed for eCalc
          - NAME: Produced water reinjection pump
            CATEGORY: PUMP
            ENERGY_USAGE_MODEL:
              TYPE: PUMP
              CONDITION: $var.produced_water_reinjection_condition
              ENERGYFUNCTION: pump_chart
              RATE: $var.produced_water_reinjection_total_system_rate_m3_per_day
              FLUID_DENSITY: 1010
              SUCTION_PRESSURE: 10  # bara
              DISCHARGE_PRESSURE: 200  # bara
          - NAME: Sea water injection pump
            CATEGORY: PUMP
            ENERGY_USAGE_MODEL:
              TYPE: TABULATED
              ENERGYFUNCTION: pump_sampled
              VARIABLES:
                - NAME: RATE
                  EXPRESSION: $var.salt_water_injection_rate_m3_per_day
    FUELCONSUMERS:
      - NAME: Flare
        CATEGORY: FLARE
        ENERGY_USAGE_MODEL:
          TYPE: DIRECT
          FUELRATE: $var.flare_fuel_rate_sm3_day
      - NAME: Gas export compressor
        CATEGORY: COMPRESSOR
        ENERGY_USAGE_MODEL:
          TYPE: COMPRESSOR
          ENERGYFUNCTION: compressor_with_turbine_sampled
          RATE: $var.gas_export_rate_sm3_per_day
          SUCTION_PRESSURE: 50 #not used but a number is needed for eCalc
          DISCHARGE_PRESSURE: 200 #not used but a number is needed for eCalc
~~~~~~~~

## Input files
~~~~~~~~text title="compressor_sampled.csv"
RATE,POWER
#[Sm3/day],[MW]
0,0
1,4.1
100000000,4.1
200000000,4.1
210000000,4.1
220000000,4.4
230000000,4.8
240000000,5.1
250000000,5.4
260000000,5.8
270000000,6.1
280000000,6.4
290000000,6.8
300000000,7.1
500000000,14.2
~~~~~~~~

~~~~~~~~text title="compressor_sampled_with_turbine.csv"
RATE,FUEL
#[Sm3/day],[Sm3/day]
0,0
0.1,50000
3000000,50000
3500000,130000
7000000,170000
~~~~~~~~

~~~~~~~~text title="genset.csv"
POWER,FUEL
#[MW],[Sm3/day]
0,     0
0.1,   65000
10.0,  75000
20.0,  126000
40.0,  250000
100.0, 750000
~~~~~~~~

~~~~~~~~text title="pump_chart.csv"
SPEED,RATE,HEAD,EFFICIENCY
3250,250,2640,59
3250,360,2490,68
3250,500,2342,77
3250,600,2210,80
3250,667,2068,78
3250,735,1870,74
~~~~~~~~

~~~~~~~~text title="pump_sampled.csv"
RATE,POWER
#[Sm3/day],[MW]
0,0
1,3
8500,4
9000,4
17000,6
17500,9
36000,13
~~~~~~~~

~~~~~~~~text title="production_data.csv"
Dates,                  OIL_PROD,  GAS_PROD,    WATER_PROD, WATER_INJ,  GAS_INJ,    GAS_LIFT
#,                      Sm3/d,     Sm3/d,       m3/d,       m3/d,       Sm3/d,      Sm3/d
2020-01-01 00:00:00,    9000,       3500000,    18000,      34000,      2200000,    130000
2021-01-01 00:00:00,    8000,       3600000,    19000,      33000,      2200000,    170000
2022-01-01 00:00:00,    7000,       3700000,    15000,      30000,      2200000,    210000
2023-01-01 00:00:00,    6000,       3800000,    16000,      33000,      2300000,    240000
2024-01-01 00:00:00,    6000,       3900000,    14000,      35000,      2300000,    280000
2024-12-01 00:00:00,    6000,       4000000,    15000,      36000,      2400000,    310000
2026-01-01 00:00:00,    7000,       4100000,    18000,      36000,      2400000,    350000
2027-01-01 00:00:00,    6000,       4500000,    15000,      38000,      2400000,    390000
2028-01-01 00:00:00,    6000,       3500000,    12000,      33000,      2400000,    430000
2029-01-01 00:00:00,    5000,       2500000,    14000,      36000,      2400000,    460000
2030-01-01 00:00:00,    6000,       2000000,    16000,      35000,      2400000,    500000
2031-01-01 00:00:00,    4000,       3000000,    14000,      33000,      2400000,    530000
~~~~~~~~
