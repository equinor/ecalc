## Added

- `PUMP_SIMULATIONS` can be evaluated. Each period gets the stream distribution setting that was used and, for every pump, its rate, speed, recirculation, choke pressure drop and power, and whether it is within its chart. Pumps can be in parallel, with a common stream or a stream each, and in series. A pump with `PRESSURE_CONTROL: NONE` is not valid when its discharge pressure is above `OUTLET_PRESSURE`.
