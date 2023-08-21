# ENERGY_USAGE_MODEL

[INSTALLATIONS](INSTALLATIONS) /
[...] /
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL)


 | Required   | Child of                  | Children/Options                   |
 |------------|---------------------------|------------------------------------|
 | Yes        | `FUELCONSUMERS`      | `COMPRESSORS`                 |
 |            | `CONSUMERS`          | `CONDITION`  <br /> `CONDITIONS`  <br /> `CONSUMPTION_RATE_TYPE` <br /> `DISCHARGE_PRESSURE` <br /> `ENERGYFUNCTION` <br /> `FLUID_DENSITY` <br /> `FUELRATE` <br /> `LOAD` <br /> `OPERATIONAL_SETTINGS` <br /> `POWERLOSSFACTOR` <br /> `PUMPS` <br /> `RATE` <br /> `SUCTION_PRESSURE` <br /> `TOTAL_SYSTEM_RATE` <br /> `TYPE`  <br /> `VARIABLES`      |

## Description

The energy usage model specifies the data to calculate the energy usage of a consumer. This data is used to set up a
function that may be evaluated for a set of time series and returns a result including the calculated energy usage.

The type of energy usage model is defined by `TYPE`, and which keywords are required/supported will be different
for each type. The available types are:

Energy usage model types:

* [DIRECT](../../modelling/setup/installations/direct_consumers)
* [TABULATED](../../modelling/setup/installations/tabular_models_in_calculations)
* [PUMP](../../modelling/setup/installations/pump_models_in_calculations#pump-energy-usage-model)
* [PUMP_SYSTEM](../../modelling/setup/installations/pump_models_in_calculations#pump_system-energy-usage-model)
* [COMPRESSOR](../../modelling/setup/installations/compressor_models_in_calculations/compressor)
* [COMPRESSOR_SYSTEM](../../modelling/setup/installations/compressor_models_in_calculations/compressor_system)
* [VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES](../../modelling/setup/installations/compressor_models_in_calculations/variable_speed_compressor_train_model_with_multiple_streams_and_pressures)

For all types, the keywords [CONDITION](CONDITION.md), [CONDITIONS](CONDITIONS.md) and [POWERLOSSFACTOR](POWERLOSSFACTOR.md) are optional and supported, and these will act
on the calculated energy usage after the calculated energy usage from the model defined by [TYPE](TYPE.md).

## Temporal energy usage model

It is possible to update the energy model within a consumer over time, as long as the
`ENERGY_USAGE_MODEL` stays within one type. The `TYPE` cannot change over time. In case `TYPE` evolution is needed, we recommend that you split the model into two [CONSUMERS](CONSUMERS.md).

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  2020-01-01:
    TYPE: TABULATED
    ENERGYFUNCTION: tabulated_energy_function_reference_initial
    VARIABLES:
      - NAME: RATE
        EXPRESSION: SIM1;GAS_PROD
  2022-01-01:
    TYPE: TABULATED
    ENERGYFUNCTION: tabulated_energy_function_reference_new
    VARIABLES:
      - NAME: RATE
        EXPRESSION: SIM1;GAS_PROD
~~~~~~~~

