# CONDITIONS

[INSTALLATIONS](/about/references/INSTALLATIONS.md) /
[...] /
[ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) /
[CONDITIONS](/about/references/CONDITIONS.md)

| Required | Child of             | Children/Options |
|----------|----------------------|------------------|
| No       | `ENERGY_USAGE_MODEL` | None             |

## Description

Specify several conditions that all should be true for the condition to be true, i.e. a logical AND operation.
See [CONDITION](/about/references/CONDITION.md).

## Format

~~~~~~~~yaml
CONDITIONS:
  - <CONDITION>
  - <CONDITION>
~~~~~~~~

