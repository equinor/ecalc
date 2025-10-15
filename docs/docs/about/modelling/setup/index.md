---
title: Setup an eCalc™ Model
sidebar_position: 2
description: Guide on how to setup an eCalc™ model
---

# Set up an eCalc Model
This section first describes how to create your own eCalc™ model file, which consists of the following six separate
sections: 

| Input                                                              | Function                                                                                                                                                                                          |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [TIME_SERIES](/about/modelling/setup/time_series.md)               | Input of time dependent variables. For example, production profiles for an installation                                                                                                           |
| [FACILITY_INPUTS](/about/modelling/setup/facility_inputs/index.md) | Input of generator sets, and facility equipment that consumes either power or fuel *(with the exception of compressors that are modelled with compressor charts)*                                |
| [MODELS](/about/modelling/setup/models/index.md)                   | Input of compressor models that use compressor charts. Gas turbines that are directly coupled to a compressor are also included here                                                              |
| [FUEL_TYPES](/about/modelling/setup/fuel_types.md)                 | Input of the various fuel types used in the specified installation(s)                                                                                                                             |
| [VARIABLES](/about/modelling/setup/variables.md)                   | Input of variables that can reference to in expressions within the YAML set-up file                                                                                                               |
| [INSTALLATIONS](/about/modelling/setup/installations/index.md)     | This is essentially the only *"output"* section in the YAML setup file. All the inputs are specified and related to specific platforms/rigs, and whether or not they consume either power or fuel |

All of the above are mandatory inputs for eCalc™ to run, except for models (which is an optional, but still important input) and variables.

The section ends with some general information about [File formats and syntax](/about/modelling/setup/file_format_and_syntax/index.md),
with some specific details about writing [Expressions](/about/modelling/setup/file_format_and_syntax/expressions.md)
in the YAML file, and some information about how [eCalc™ interprets the time input](/about/modelling/setup/time_in_ecalc/index.md)
given in various parts of the YAML file.