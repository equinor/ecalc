## Added

- `ENERGY_NETWORK`: `ELECTRICAL_CONSUMER` and `MECHANICAL_CONSUMER` `LOAD`, and `FUEL_GAS_CONSUMER` and `DIESEL_CONSUMER` `RATE`, can each be a 1D curve (inline or FILE) looked up by a variable, instead of a direct expression. This replaces the current usage of the legacy `TABULAR` facility model, which is 1D (mostly rate vs. power) in practice.
- `COMPRESSORS`: added the physical compressors in the model, each with a required unique `NAME` and an optional `ALIAS`. Compressor process units in `PROCESS_PIPELINES` and `COMPRESSOR_SAMPLED` units in `ENERGY_NETWORK` refer to a compressor with `COMPRESSOR`, which replaces `NAME` on compressor process units.

## Changed

- `SHAFTS`: each shaft lists the compressors on it with `COMPRESSORS`, which replaces `SHAFT` on compressor process units in `PROCESS_PIPELINES`. A compressor placed in a process pipeline must be on a shaft, and a `DRIVE_TRAIN` must drive a shaft whose compressors are all solved by a process simulation.
- `PROCESS_PIPELINES`: a `REBUNDLE` event's `CHANGE_TARGET` must be the `COMPRESSOR` of a compressor process unit in the same pipeline. Other targets give a validation error listing the pipeline's compressors.
