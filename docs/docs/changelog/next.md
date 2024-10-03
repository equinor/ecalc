---
slug: latest
title: Next
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -1002
---

# eCalc



## New Features

- In the results, the fluid streams entering and leaving a compressor train are now defined separately from the fluid
  streams entering and leaving the individual compressor stages (pressure, temperature, composition, density, etc.).
  This used to be covered only by reporting the inlet/outlet pressures before choking.
  If there is any upstream choking, this will happen between the inlet of the compressor train, and the inlet of the
  first compressor stage. This means that in a situation with upstream choking, the fluid stream entering the compressor
  train will have higher e.g. pressure and density than the fluid stream entering the first compressor stage. If there
  is any downstream choking, this will happen between the outlet of the last compressor stage and the outlet of the
  compressor train. This means that in a situation with downstream choking, the fluid stream leaving the compressor
  train will have lower e.g. pressure and density than the fluid stream leaving the last compressor stage.
- `POWER_ADJUSTMENT_FACTOR` for models: Optional factor to adjust the power (MW). Previously only the
  `POWER_ADJUSTMENT_CONSTANT` has been available for models, now it is possible to adjust/scale the power with a
  constant and a factor. It can be used to calibrate equipment.

## Fixes

- If a compressor train is not able to reach the requested inlet or outlet pressure, both the compressor stages and
  the compressor train used to be reported as invalid. This is now changed. If the compressor stages are operating within
  their capacity, they will now be reported as valid even if the compressor train as a whole is not able to reach
  the requested inlet or outlet pressures.

- Emission intensities are no longer calculated and reported in the results, due to the following discrepancies:
CO2 intensity is defined as the total emission divided by the total HC export. eCalc only calculates the future data, so the correct CO2 intensity should be found by adding the historical to these future data. The hydrocarbon export rate is still reported to help the user calculate the CO2 intensity outside of eCalc.
Methane intensity was incorrectly calculated based on HC export. The common definition is the methane emission divided by the natural gas throughput of the wanted equipment- or installation level. This is safest done outside of eCalc to ensure proper definition.
## Breaking changes

- This version includes a rewrite of the yaml validation, which should catch more errors than before.

    Main changes:
    - Economics has been removed. TAX, PRICE and QUOTA keywords will now give an error.
    - Misplaced keywords will now cause an error instead of being ignored.

- H2O is no longer supported in composition. Use 'water' instead.

- The CLI command `ecalc show results` has been removed. The reason being additional maintenance for something that did not seem to be used a lot.
