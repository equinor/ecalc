---
slug: latest
title: Next
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: 1
---

# eCalc



## New Features

- Added chart area flag NO_FLOW_RATE to the possible statuses for an operational point in a variable speed compressor chart. The chart area flags can currently only be found in the json result file, but we will also try to find a way of displaying this information in the WebApp as well.
- Whenever there is a variable speed compressor only recirculation fluid (can happen in a multiple streams and pressures compressor train) a warning will be logged.


## Fixes
- `nmvoc` emissions were incorrectly reported for the ltp categories `HEATER` and `BOILER`: The emission query filters included `nox`, and are now corrected to `nmvoc`.

## Breaking changes


