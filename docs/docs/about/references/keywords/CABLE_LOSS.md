# CABLE_LOSS

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) /
[GENERATORSETS](/about/references/keywords/GENERATORSETS.md)

## Description

Fraction, describing power loss from shore. Used to calculate actual power supply onshore.

## Format

~~~~~~~~yaml

CABLE_LOSS: <file or value>
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