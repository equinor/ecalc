---
title: Modelling Guide
sidebar_position: 4
description: eCalc modelling
---

# Modelling
This section describes how to use eCalc.
:::tip
It is good practice when writing the eCalc YAML setup file to include, as comments, the version it was written for, your name and a ‘change log’ which should include the date and changes made.
:::

The YAML setup file:

~~~~~~~~yaml
# ecalc version v5.3.1
# input by: john.doe@example.com
#
# change log - add comments regarding relevant changes made to the file
# date: YYYYMMDD, john doe
# extended suction and discharge pressure range for precompressor
# date: YYYYMMDD, jane doe
# updated gensetA

TIME_SERIES:
  - NAME: SIM1
    FILE: examplecase_inputvariables.csv
    TYPE: DEFAULT
FACILITY_INPUTS:
...
~~~~~~~~

