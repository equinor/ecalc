## Added

- `ENERGY_NETWORK`: a `DRIVE_TRAIN` can give the mechanical efficiency of each compressor on its shaft in `MECHANICAL_EFFICIENCIES`, as a `COMPRESSOR` and its `EFFICIENCY`, a number or an expression. A compressor demands its gas power divided by its mechanical efficiency as shaft power. A compressor not listed has efficiency 1.0, so existing results do not change.

## Changed

- `DEFINITIONS`: compressor models are defined in `COMPRESSOR_MODELS`, which replaces `TYPE: COMPRESSOR` process units in `DEFINITIONS.PROCESS_UNITS`. A compressor process unit gives its model with `MODEL` instead of `TARGET`, and a `REBUNDLE` event gives the new model with `CHANGE_TO`. Both take a model in place or the name of one in `COMPRESSOR_MODELS`. `CHANGE_FROM` is removed, since the model before the event is known.

## Removed

- `PROCESS_PIPELINES`: `DEFINITIONS.PROCESS_UNITS` and `TARGET` are removed, so a process unit can no longer be reused from `DEFINITIONS`. Each entry in a pipeline's `PROCESS_UNITS` is a process unit given by its `TYPE` and that type's keys, and `NAME` on process units is removed. A compressor process unit has `TYPE: COMPRESSOR` and is the only process unit referred to by name, its `COMPRESSOR`. A constraint's `PROCESS_UNIT` must be the `COMPRESSOR` of a compressor process unit in its pipeline.
