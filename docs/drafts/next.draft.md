---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -55
---

# eCalc {{ version }}

## Features

## Bug Fixes

- The calculated power result has up until now not been checked against `MAXIMUM_POWER` for **SIMPLIFIED TRAINS**. This is now fixed. If the power is above `MAXIMUM_POWER`, the result will not be valid.
- `CONDITION` and `CONDITIONS` on `VENTING_EMITTERS` had no effect. This is now fixed.

## Breaking changes

## CLI
