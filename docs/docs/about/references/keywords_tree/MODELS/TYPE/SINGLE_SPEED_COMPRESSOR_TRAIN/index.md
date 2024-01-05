---
sidebar_position: 3
---

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md) :
[SINGLE_SPEED_COMPRESSOR_TRAIN](/about/references/keywords_tree/MODELS/TYPE/SINGLE_SPEED_COMPRESSOR_TRAIN/index.md) /

# SINGLE_SPEED_COMPRESSOR_TRAIN
The single speed compressor train model is modelling one or more single speed compressors mounted on a common shaft.
Being single speed compressors on a common shaft means that all compressors will run at the exact same fixed speed, and
this shaft speed can not be varied. Since the shaft speed can not vary, the problem is overdefined given the rate,
suction pressure and discharge pressure. A method for controlling the pressure also needs to be defined, to be able
to calculate the energy usage for given rates, suction pressures and discharge pressures.

This means that a single speed compressor model needs the following to be defined:

- A polytropic compressor chart for every compressor stage in the compressor train. For single speed trains, eCalc
  only supports user defined single speed compressor charts.
- A [FLUID MODEL](/about/modelling/setup/models/fluid_model.md).
- A [PRESSURE_CONTROL](/about/modelling/setup/models/compressor_modelling/fixed_speed_pressure_control/index.md).



The model is defined under the main keyword [MODELS](/about/references/keywords_tree/MODELS/index.md) in the format

## Format

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: SINGLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: <reference to fluid model>
    PRESSURE_CONTROL: <method for pressure control, DOWNSTREAM_CHOKE (default), UPSTREAM_CHOKE, , INDIVIDUAL_ASV_PRESSURE, INDIVIDUAL_ASV_RATE or COMMON_ASV>
    MAXIMUM_DISCHARGE_PRESSURE: <Maximum discharge pressure in bar (can only use if pressure control is DOWNSTREAM_CHOKE)>
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model for first stage, must be defined in MODELS or FACILITY_INPUTS>
          PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model for second stage, must be defined in MODELS or FACILITY_INPUTS>
          PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
        - ... and so forth for each stage in the train
    POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
    MAXIMUM_POWER: <Optional constant MW maximum power the compressor train can require>
    CALCULATE_MAX_RATE: <Optional compressor train max standard rate [Sm3/day] in result if set to true. Default false. Use with caution. This will increase runtime significantly. >
~~~~~~~~
