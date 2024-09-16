---
slug: latest
title: Next
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -1002
---

# eCalc



## New Features
- `POWER_ADJUSTMENT_FACTOR` for models: Optional factor to adjust the power (MW). Previously only the `POWER_ADJUSTMENT_CONSTANT` has been available for models, now it is possible to adjust/scale the power with a constant and a factor. It can be used to calibrate equipment.

## Fixes

- If a compressor train is not able to reach the requested inlet or outlet pressure, both the compressor stages and
  the compressor train used to be reported as invalid. This is now changed. If the compressor stages are operating within
  their capacity, they will now be reported as valid even if the compressor train as a whole is not able to reach
  the requested inlet or outlet pressures.

## Breaking changes

- This version includes a rewrite of the yaml validation, which should catch more errors than before.
    
    Main changes:
    - Economics has been removed. TAX, PRICE and QUOTA keywords will now give an error.
    - Misplaced keywords will now cause an error instead of being ignored.
