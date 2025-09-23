---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -52
---

# eCalc {{ version }}

## Features

## Bug Fixes

## Breaking changes

- We now require all references to be unique, i.e. names in FACILITY_INPUTS, MODELS and FUEL_TYPES should not be the same across the different keywords.

### CLI

- Remove `operational_settings_results` from compressor/pump system json result. In most use-cases this result isn't used.
  If you used this result, let us know, then we can consider supporting your use-case.
