---
title: VENTING_EMITTERS
sidebar_position: 6
description: eCalc KEYWORDS
---
# VENTING_EMITTERS

<span className="major-change-new-feature"> New definition of VENTING_EMITTERS from eCalc v8.8!
</span> 
<br></br>

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) / 
[VENTING_EMITTERS](/about/references/keywords_tree/VENTING_EMITTERS/index.md)


| Required | Child of                  | Children/Options                             |
|----------|---------------------------|----------------------------------------------|
| No       | `INSTALLATIONS`      | `NAME` <br /> `CATEGORY`  <br />  `EMISSION` |

:::important
- eCalc version 8.8: Updated definition of VENTING_EMITTERS. New keyword [EMISSION](/about/references/keywords_tree/VENTING_EMITTERS/EMISSION/index.md) is replacing [EMITTER_MODEL](/about/references/keywords/EMITTER_MODEL.md) and [EMISSION_NAME](/about/references/keywords/EMISSION_NAME.md). Now possible to define `UNIT` and `TYPE` for emission rate.  
- eCalc version 8.7: [VENTING_EMITTERS](/about/references/keywords_tree/VENTING_EMITTERS/index.md) keyword is replacing the [DIRECT_EMITTERS](/about/references/keywords/DIRECT_EMITTERS.md) keyword.
- eCalc version 8.6 and earlier: Use DIRECT_EMITTERS as before.
:::


## Description - eCalc version 8.7 and before:
The [VENTING_EMITTERS](/about/references/keywords/VENTING_EMITTERS_TREE/index.md) keyword covers the direct emissions on the installation
that are not consuming energy. The attributes [NAME](/about/references/keywords/NAME.md),
[EMISSION_NAME](/about/references/keywords/EMISSION_NAME.md), [CATEGORY](/about/references/keywords/CATEGORY.md) and
[EMITTER_MODEL](/about/references/keywords/EMITTER_MODEL.md) are required.

## Format
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: <emitter name>
    EMISSION_NAME: <emission name>
    CATEGORY: <category>
    EMITTER_MODEL: <emitter model>
~~~~~~~~

## Example
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: SomeVentingEmitter
    EMISSION_NAME: CH4
    CATEGORY: COLD-VENTING-FUGITIVE
    EMITTER_MODEL:
      <emitter model data>
  ...
  - NAME: SomeOtherVentingEmitter
    EMISSION_NAME: C2H6
    CATEGORY: COLD-VENTING-FUGITIVE
    EMITTER_MODEL:
      <emitter model data>
~~~~~~~~

## Description - eCalc from version 8.8:
The attributes [NAME](/about/references/keywords/NAME.md), [CATEGORY](/about/references/keywords/CATEGORY.md) and
[EMISSION](/about/references/keywords/VENTING_EMITTERS_TREE/EMISSION/index.md) are required.

## Format
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: <emitter name>
    CATEGORY: <category>
    EMISSION:
      <emission data>

~~~~~~~~

## Example
~~~~~~~~yaml
VENTING_EMITTERS:
  - NAME: SomeVentingEmitter
    CATEGORY: COLD-VENTING-FUGITIVE
    EMISSION:
      <emission data>
  ...
  - NAME: SomeOtherVentingEmitter
    CATEGORY: COLD-VENTING-FUGITIVE
    EMISSION:
      <emission data>
~~~~~~~~
