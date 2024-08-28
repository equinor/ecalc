---
slug: latest
title: Next
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -1002
---

# eCalc



## New Features


## Fixes


## Breaking changes

- This version includes a rewrite of the yaml validation, which should catch more errors than before.
    
    Main changes:
    - Economics has been removed. TAX, PRICE and QUOTA keywords will now give an error.
    - Misplaced keywords will now cause an error instead of being ignored.
