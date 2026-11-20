## Added

- `ENERGY_NETWORK`: capacities can be expressions, and capacity shortfalls are reported.
- `ENERGY_NETWORK`: junctions allocate demand across multiple inputs, with per-input dispatch limits.
- `ENERGY_NETWORK`: added `COMPRESSOR_SAMPLED` units. Sampled compressor tables extrapolate using the convex hull of the sampled data.

## Changed

- `PROCESS_SIMULATIONS`: solver constraints use a relative tolerance, improving convergence for large values.
