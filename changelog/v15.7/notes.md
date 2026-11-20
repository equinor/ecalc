## Changed

- `ENERGY_NETWORK`: a compressor's `EFFICIENCY` in a `DRIVE_TRAIN`'s `MECHANICAL_EFFICIENCIES` covers its share of the gearbox and couplings as well as its bearings and seals, not the driver's own losses. A compressor-only value, for example from a datasheet, should be multiplied by the gearbox efficiency.
- `ENERGY_NETWORK`: a `COMPRESSOR_SAMPLED` unit's `FILE` has a `MECHANICAL_POWER` [MW] column, replacing `FUEL` and `POWER`, and its `INPUT` must provide mechanical power, e.g. a `GAS_TURBINE` or an `ELECTRICAL_MOTOR`. The gas turbine generated for a file with both `FUEL` and `POWER` is removed; declare a `GAS_TURBINE` as `INPUT` instead. See [Migrate COMPRESSOR_SAMPLED](../about/nextgen/migrate-compressor-sampled.mdx) for how to convert a `FILE` with `POWER` and `FUEL` into a `MECHANICAL_POWER` file and a gas turbine curve.
- `PUMP_PROCESS_SIMULATIONS`: `OUTLET_PRESSURE` replaces `REQUIRED_DISCHARGE_PRESSURE`. It is the pressure requested downstream of the choke, which can be lower than the pump's discharge pressure. Results do not change.

## Removed

- `ENERGY_NETWORK`: `NAME` is removed from `COMPRESSOR_SAMPLED` and `DRIVE_TRAIN`. A `COMPRESSOR_SAMPLED` unit is named by its `COMPRESSOR`, which must differ from the names of sources and units, and a `DRIVE_TRAIN` is identified by its `SHAFT`.
