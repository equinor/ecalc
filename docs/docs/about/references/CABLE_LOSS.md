# CABLE_LOSS

[INSTALLATIONS](/about/references/INSTALLATIONS.md) /
[GENERATORSETS](/about/references/GENERATORSETS.md)

## Description

Fraction, describing power loss from shore. Used to calculate actual power supply onshore. Relevant only for generatorsets of [CATEGORY](/about/references/CATEGORY.md) `POWER-FROM-SHORE`.

## Format

~~~~~~~~yaml

CABLE_LOSS: <expression or value>
~~~~~~~~

## Examples
10 percent power loss from shore:
~~~~~~~~yaml

CABLE_LOSS: 0.1
~~~~~~~~

Cable loss defined as time series in file (PFS):
~~~~~~~~yaml

CABLE_LOSS: PFS;CABLE_LOSS
~~~~~~~~