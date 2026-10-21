---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -72
---

# eCalc {{ version }}

## Features

## Bug Fixes

- Liquid removal now correctly removes both water and hydrocarbon liquid phases, instead of only accounting for one.
- NextGen individual anti-surge recirculation is now added directly in front of each compressor, after the stage cooler and liquid remover. For rich gas, part of the recirculated gas was previously removed as liquid, which could leave compressors below the surge line and reduce the outlet rate.

## Breaking changes

### CLI
