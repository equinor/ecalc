---
title: Compressor
sidebar_position: 1
description: COMPRESSOR Energy Usage Model
---

# COMPRESSOR Energy Usage Model

When `COMPRESSOR` is specified under [ENERGY_USAGE_MODEL](../../../../references/keywords/ENERGY_USAGE_MODEL) the only keyword that is allowed is [ENERGYFUNCTION](../../../../references/keywords/ENERGYFUNCTION).
This model only supports a single compressor, which can either be a tabular compressor model defined in [FACILITY_INPUTS](../../facility_inputs/index.md)  or a compressor model defined in [MODELS](../../models/index.md).

The attributes [RATE](../../../../references/keywords/RATE), [SUCTION_PRESSURE](../../../../references/keywords/SUCTION_PRESSURE) and
[DISCHARGE_PRESSURE](../../../../references/keywords/DISCHARGE_PRESSURE) are required to be specified in the energy usage model. Here, the specified rate will be for the entire train, the
suction pressure will be at the inlet of the first stage, whilst the discharge pressure will be the outlet pressure of the last stage.

## Format

~~~~~~~~yaml
NAME: <Reference name>
TYPE: COMPRESSOR
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR
  CONDITION: <condition expression>
  ENERGYFUNCTION: <reference to energy function in facility inputs or models of compressor type>
  RATE: <rate expression>
  SUCTION_PRESSURE: <suction pressure expression>
  DISCHARGE_PRESSURE: <discharge pressure expression>
~~~~~~~~

## Example

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR
  ENERGYFUNCTION: booster_compressor_reference
  RATE: SIM1;GAS_PROD
  SUCTION_PRESSURE: SIM1;SUCTION_PRESSURE
  DISCHARGE_PRESSURE: SIM1;DISCHARGE_PRESSURE
~~~~~~~~