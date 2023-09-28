---
title: Variable speed compressor train model with multiple streams and pressures
sidebar_position: 4
---

This compressor type is a more advanced model which covers compressor trains which may have multiple ingoing and/or outgoing streams and/or extra pressure controls. The figure below is an example of what this compression train could look like.

![Compressor train with multiple streams and pressures](process_compressor_train_multiple_streams.png)

## Format

The model is defined under the main keyword [MODELS](/about/references/keywords/MODELS.md) in the format:

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    # All streams defined ahead of stage
    # Default outlet stream after last stage should not be defined
    STREAMS: # All inlet streams must have fluid models with the same eos model
      - NAME: <name of stream 1>
        TYPE: INGOING
        FLUID_MODEL: <reference to fluid model, must be defined in MODELS>
      - NAME: <name of stream 2>
        TYPE: INGOING
        FLUID_MODEL: <reference to fluid model, must be defined in MODELS>
      - ...
      - NAME: <name of stream N>
        TYPE: OUTGOING # NB: No fluid definition for outgoing streams!
    STAGES:
      - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
        COMPRESSOR_CHART: <reference to a compressor chart model defined in MODELS>
        STREAM: <reference stream from STREAMS. Needs to be an INGOING type stream.>
        CONTROL_MARGIN: <Default value 0.0>
        PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
        CONTROL_MARGIN_UNIT: <FRACTION or PERCENTAGE, default is PERCENTAGE>
      - ...
      - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
        COMPRESSOR_CHART: <reference to a compressor chart model defined in MODELS>
        STREAM: <Optional>
        - <reference stream from STREAMS for one in- or outgoing stream. Optional>
        - <reference stream from STREAMS for another in- or outgoing stream. Optional>
        CONTROL_MARGIN: <Default value 0.0>
        CONTROL_MARGIN_UNIT: <FRACTION or PERCENTAGE, default is PERCENTAGE>
        PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
        INTERSTAGE_CONTROL_PRESSURE:
          UPSTREAM_PRESSURE_CONTROL: <pressure control>
          DOWNSTREAM_PRESSURE_CONTROL: <pressure control>
      - ...
      - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
        COMPRESSOR_CHART: <reference to a compressor chart model defined in MODELS>
        CONTROL_MARGIN: <Default value 0.0>
        CONTROL_MARGIN_UNIT: <FRACTION or PERCENTAGE, default is PERCENTAGE>
        PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
      - ...
    MAXIMUM_POWER: <Optional constant MW maximum power the compressor train can require>
~~~~~~~~

## Keyword usage

- [STREAMS](/about/references/keywords/STREAMS.md) is a list of all in- and out-going streams for the compressor train.
  - The same equation of state (EOS) must be used for each INGOING stream fluid models
  - OUTGOING fluid models **cannot** be specified.
  
- `STAGES` is a list of all the stages in the compressor train. 
  - For each stage, a temperature in Celsius must be defined. It
is assumed that the gas is cooled down to this temperature ahead of the compression at this stage. 
  - A reference to a
compressor chart needs to be specified for each stage.
  - For the first stage, it is required to have **at least** one stream of INGOING type. In addition, `INTERSTAGE_CONTROL_PRESSURE` cannot be used on the first stage.
  - Stages 2, ..., N may have a stream defined and it may be in- or outgoing. If an ingoing stream is defined, this stream
will be mixed with the outlet stream of the previous stage, obtaining a composition for the mixed fluid based on the
molar fractions and rate for each of them. If an outgoing stream is defined, the rate continuing to the next stage, will
be subtracted the rate of the outgoing stream.

- `PRESSURE_DROP_AHEAD_OF_STAGE` is optional, but if defined it will reduce the inlet pressure of that particular stage by a fixed value.
As of now, only a single value is supported - i.e. a time series cannot be used here.

- `CONTROL_MARGIN` is a surge control margin, see [Surge control margin for variable speed compressor chart](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md).

- `CONTROL_MARGIN_UNIT` is the unit of the surge control margin.

### INTERSTAGE_PRESSURE_CONTROL

:::note
`INTERSTAGE_CONTROL_PRESSURE` may be specified for one (only one!) of the stages 2, ..., N. It may **not** be specified for the first stage. See [INTERSTAGE_CONTROL_PRESSURE](/about/references/keywords/INTERSTAGE_CONTROL_PRESSURE.md) for more usage details
:::

This is optional but essentially when this is specified the compression train is split into two parts - before and after the `INTERSTAGE_CONTROL_PRESSURE`. As all rates and pressures (suction, discharge and interstage) are known, each side of the compression train can be solved independently.

Thus, given this, the rotational speed needed to match the suction and interstage pressure can be found. This speed will be for the first section of the compression train. The same is done for the second part of the train, only here the rotational speed is found to match the interstage and discharge pressure, for the given rates.

The highest speed between the first and second parts of the train is then taken as the rotational speed of the compression train.
This speed will essentially be needed to meet the most demanding pressure interval.
The section with the lower rotational speed must then be run with a form of pressure control (see [UPSTREAM_PRESSURE_CONTROL](/about/references/keywords/UPSTREAM_PRESSURE_CONTROL.md)/[DOWNSTREAM_PRESSURE_CONTROL](/about/references/keywords/DOWNSTREAM_PRESSURE_CONTROL.md)).

In a given simulation, the section of the compression train that requires either upstream or downstream pressure control is not fixed. This means that for different time steps, the part of the train with the highest rotational speed is not set to either the first or second section. Thus, both pressure control methods must be specified but only one of them will be used for each time step.

Technically, the INTERSTAGE_PRESSURE_CONTROL may be set independent of where the streams are defined. I.e. it may be
defined at a stage where there is an in- or out-going stream defined, or at a stage where there is no defined stream.
In reality, the INTERSTAGE_PRESSURE_CONTROL is linked to a stream, for example an outgoing stream for export where the
export pressure is defined, and where the rest of the gas continues through the compressor train for example for
injection at a higher pressure.

### Fixed pressure control

The available pressure controls are
* DOWNSTREAM_CHOKE
* UPSTREAM_CHOKE
* INDIVIDUAL_ASV_PRESSURE
* INDIVIDUAL_ASV_RATE
* COMMON_ASV

The sub-train where the pressure control is used, is now modeling wise equal to a single speed train as the speed is
determined from the other sub-train. The inlet and outlet pressures for a sub-train, may be either the suction pressure
and the interstage control pressure or interstage control pressure and the discharge pressure, depending on which sub
part governs the speed of the full train.

See [FIXED PRESSURE CONTROL](/about/modelling/setup/models/compressor_modelling/fixed_speed_pressure_control/index.md) for more details.

## Example

~~~~~~~~yaml
MODELS:
  - NAME: compressor_model
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    STREAMS: 
      - NAME: 1_stage_inlet
        TYPE: INGOING
        FLUID_MODEL: fluid_model_1
      - NAME: 3_stage_inlet
        TYPE: INGOING
        FLUID_MODEL: fluid_model_2
      - NAME: 2_stage_outlet
        TYPE: OUTGOING
    STAGES:
      - COMPRESSOR_CHART: 1_stage_chart
        INLET_TEMPERATURE: 20
        STREAM: 
          - 1_stage_inlet
      - COMPRESSOR_CHART: 2_stage_chart 
        INLET_TEMPERATURE: 30
      - COMPRESSOR_CHART: 3_stage_chart 
        INLET_TEMPERATURE: 35
        STREAM: 
          - 2_stage_outlet
          - 3_stage_inlet
        INTERSTAGE_CONTROL_PRESSURE:
          UPSTREAM_PRESSURE_CONTROL: INDIVIDUAL_ASV_RATE  #1st and 2nd stage
          DOWNSTREAM_PRESSURE_CONTROL: INDIVIDUAL_ASV_RATE #3rd and 4th stage
      - COMPRESSOR_CHART: 4_stage_chart 
        INLET_TEMPERATURE: 15
~~~~~~~~
