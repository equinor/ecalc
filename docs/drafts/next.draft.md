---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -58
---

# eCalc {{ version }}

## Features
###  Cache max sizes now configurable
- User can now set max cache sizes for reference fluid cache and fluid flas cache with a cache config.

Note: default values can be used and covers all normal cases seen so far.

Note: To disable cache set sizes to zero

To set these when using as library set config like this:
~~~
NeqSimFluidService.configure(CacheConfig(reference_fluid_max_size=100, flash_max_size=200_000))
~~~
Note: must be set before using NeqsimService.factory().initialize() context manager. Must be set once before app startup and can not be changed during app run.

To override default cache sizes with cli use the new optional options "--reference_cache_size" and/or "--flash_cache_size".
