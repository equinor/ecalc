---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -49
---

# eCalc {{ version }}

## Features

## Bug Fixes

- Fixed a bug in the `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES` model:
  For cases where there have been multiple streams with different compositions entering the compressor train **prior** to a
  stage where there is an interstage pressure there has been a bug in the calculations. This has had no effect on models
  where additional streams were added at of after the stage where there is an interstage pressure.

## Breaking changes
