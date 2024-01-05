---
title: RATE
sidebar_position: 1
description: eCalc KEYWORDS
---
# RATE

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) /
[VENTING_EMITTERS](/about/references/keywords_tree/VENTING_EMITTERS/index.md) /
[EMISSION](/about/references/keywords_tree/VENTING_EMITTERS/EMISSION/index.md) /
[RATE](/about/references/keywords_tree/VENTING_EMITTERS/EMISSION/RATE/index.md)


| Required | Child of   | Children/Options              |
|----------|------------|-------------------------------|
| Yes      | `EMISSION` | `VALUE`<br/>`UNIT`<br/>`TYPE` |

## Description
Emission rate. The attribute [VALUE](/about/references/keywords_tree/VENTING_EMITTERS/EMISSION/RATE/VALUE.md) is required,
while [UNIT](/about/references/keywords_tree/VENTING_EMITTERS/EMISSION/RATE/UNIT.md) and 
[TYPE](/about/references/keywords_tree/VENTING_EMITTERS/EMISSION/RATE/TYPE.md) are optional.

## Format

~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: <emitter name>
    CATEGORY: <category>
    EMISSION:
      NAME: <emission name>
      RATE:
        VALUE: <emission rate>
        UNIT: <emission rate unit, default kg/d>
        TYPE: <emission rate type, default STREAM_DAY>
~~~~~~~~


## Example

~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: SomeVentingEmitter
    CATEGORY: COLD-VENTING-FUGITIVE
    EMISSION:
      NAME: CH4
      RATE:
        VALUE: 4
        UNIT: kg/d
        TYPE: STREAM_DAY
~~~~~~~~