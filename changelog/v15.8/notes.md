## Changed

- `ENERGY_NETWORK` and `PROCESS_PIPELINES`: `EVENTS` on `GENERATOR`, `GAS_TURBINE`, `DIESEL_ENGINE` and process pipelines is renamed to `CHANGES`, so that `EVENTS` only refers to `TIMELINE.EVENTS`. Each change keeps `REF`, `CHANGE_TYPE` and `CHANGE_TO`. Using `EVENTS` gives a validation error pointing to `CHANGES`.
