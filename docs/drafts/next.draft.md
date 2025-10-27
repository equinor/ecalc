---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [ release, eCalc ]
sidebar_position: -54
---

# eCalc {{ version }}

## Features

## Bug Fixes

## Breaking changes

- Pump will return `head=0` when `rate=0`, in results. Previously `head` had a value, but was meaningless, as the pump was not flowing any fluid.

### CLI
