---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [ release, eCalc ]
sidebar_position: -54
---

# eCalc {{ version }}

## Features

- It is no longer allowed to use simplified compressor trains with unknown stages and unknown charts in a COMPRESSOR_SYSTEM. They can not be fully predefined, and can then potentially change between operational settings.

## Bug Fixes

## Breaking changes

- Pump will return `head=0` when `rate=0`, in results. Previously `head` had a value, but was meaningless, as the pump was not flowing any fluid.

### CLI
