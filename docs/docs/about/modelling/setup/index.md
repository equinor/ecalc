---
title: Setup an eCalc™ Model
sidebar_position: 2
description: Guide on how to setup an eCalc™ model
---

# Set up an eCalc Model
This section describes how to create your own eCalc™ model file. 

There are six separate sections which make up each model, these being: 

| Input | Function |
| ----- | -------- |
|[TIME_SERIES](time_series)|Input of time dependant variables. For example, production profiles for an installation|
|[FACILITY_INPUTS](facility_inputs/index.md)|Input of generator sets, and facility equipment that consumers either power or fuel *(with the exception of compressors that are modelled with compressor charts)*|
|[MODELS](models/index.md)|Input of compressor models that use compressor charts. Gas turbines that are directly coupled to a compressor are also included here|
|[FUEL_TYPES](fuel_types)|Input of the various fuel types used in the specified installation(s)|
|[VARIABLES](variables) | Input of variables that can reference to in expressions within the YAML set-up file|
|[INSTALLATIONS](installations/index.md)|This is essentially the only *"output"* section in the YAML setup file. All the inputs are specified and related to specific platforms/rigs, and whether or not they consume either power or fuel|

All of the above are mandatory inputs for eCalc™ to run, with the exception of models (which is an optional, but still important input) and variables.