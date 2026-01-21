---
title: Single speed compressor train
sidebar_position: 1
---

The single speed compressor train model is modelling one or more single speed compressors mounted on a common shaft.
Being single speed compressors on a common shaft means that all compressors will run at the exact same fixed speed, and
this shaft speed can not be varied. Since the shaft speed can not vary, the problem is overdefined given the rate,
suction pressure and discharge pressure. A method for controlling the pressure also needs to be defined, to be able
to calculate the energy usage for given rates, suction pressures and discharge pressures.

This means that a single speed compressor model needs the following to be defined:

- A polytropic compressor chart for every compressor stage in the compressor train. For single speed trains, eCalc
  only supports user defined single speed compressor charts.
- [CONTROL_MARGIN](/about/references/CONTROL_MARGIN.md) and [CONTROL_MARGIN_UNIT](/about/references/CONTROL_MARGIN_UNIT.md) for each compressor stage in the train
- [FLUID_MODEL](/about/references/FLUID_MODEL.md)
- [PRESSURE_CONTROL](/about/references/PRESSURE_CONTROL.md)

<span className="changed-from-version">
**Changed in version 9.0:** CONTROL_MARGIN and CONTROL_MARGIN_UNIT are required
</span>
<br/>

The following keywords are optional for a single speed compressor model:

- [SHAFT](/about/references/SHAFT.md) - Reference to a shaft model with mechanical efficiency
- [MAXIMUM_DISCHARGE_PRESSURE](/about/references/MAXIMUM_DISCHARGE_PRESSURE.md)
- [MAXIMUM_POWER](/about/references/MAXIMUM_POWER.md)
- [CALCULATE_MAX_RATE](/about/references/CALCULATE_MAX_RATE.md)
- [POWER_ADJUSTMENT_CONSTANT](/about/references/POWER_ADJUSTMENT_CONSTANT.md) *(Deprecated - use SHAFT instead)*

The model is defined under the main keyword [MODELS](/about/references/MODELS.md) in the format

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
          CONTROL_MARGIN: <Surge control margin for the compressor stage. Set to 0.0 if no margin>
          CONTROL_MARGIN_UNIT: <FRACTION or PERCENTAGE, default is PERCENTAGE>
          PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model for second stage, must be defined in MODELS or FACILITY_INPUTS>
          CONTROL_MARGIN: <Surge control margin for the compressor stage. Set to 0.0 if no margin>
          CONTROL_MARGIN_UNIT: <FRACTION or PERCENTAGE, default is PERCENTAGE>
          PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
        - ... and so forth for each stage in the train
    SHAFT: <Optional reference to a SHAFT model for mechanical efficiency>
    MAXIMUM_POWER: <Optional constant MW maximum power the compressor train can require>
    POWER_ADJUSTMENT_CONSTANT: <Deprecated. Use SHAFT with MECHANICAL_EFFICIENCY instead.>
    CALCULATE_MAX_RATE: <Optional compressor train max standard rate [Sm3/day] in result if set to true. Default false. Use with caution. This will increase runtime significantly. >
~~~~~~~~
