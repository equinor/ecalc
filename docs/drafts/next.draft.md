---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -61
---

# eCalc {{ version }}

## Features
STP: "flare" column has been added to STP Export - for `FIXED` installations only.

## Bug Fixes

- Hardened compressor PH flash handling so invalid thermodynamic states are no longer used in compressor outlet calculations.

## Breaking changes

### Compressor calculations

- Compressor calculations now validate PH flash results more strictly. Existing models that previously completed with invalid or non-physical PH flash states may now fail or report invalid compressor/capacity results instead.

### CLI
