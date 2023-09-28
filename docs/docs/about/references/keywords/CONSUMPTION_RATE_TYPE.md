# CONSUMPTION_RATE_TYPE

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) /
[...] / 
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) / 
[CONSUMPTION_RATE_TYPE](/about/references/keywords/CONSUMPTION_RATE_TYPE.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `ENERGY_USAGE_MODEL`      | None                               |

## Description
:::important
You must have good control of the input rates - which are stream day rates and which are calendar day rates - and
specify `CALENDAR_DAY` as input if necessary.
:::

When [REGULARITY](/about/references/keywords/REGULARITY.md) is used,the consumption rate type may be specified for
`DIRECT ENERGY USAGE MODEL`([LOAD](/about/references/keywords/LOAD.md) or [FUELRATE](/about/references/keywords/FUELRATE.md))
by setting [CONSUMPTION_RATE_TYPE](/about/references/keywords/CONSUMPTION_RATE_TYPE.md) to either `CALENDAR_DAY` or
`STREAM_DAY`.

The default behaviour, is that these will be interpreted as `STREAM_DAY` if not set explicitly. This will result in
fuel rates being multiplied by regularity to obtain (average) calendar day fuel rates, while the loads will be kept
stream day when passed to the generator set calculation.

:::note
`CALENDAR_DAY`: The average rate over a period after adjusting for operating conditions that keeps the
average throughput below the maximum achievable throughput for a single day, known as stream day.

`STREAM_DAY`: The actual rate at a given moment. When multiplied with a [REGULARITY](/about/references/keywords/REGULARITY.md)
factor you get the calendar day rate which needs to be used when evaluating the economics of a process unit.

$$
stream\ day\ rate = \frac{calendar\ day\ rate}{regularity}
$$
:::
## Format
~~~~~~~~yaml
CONSUMPTION_RATE_TYPE: <consumption_rate_type>
~~~~~~~~

Where `<consumption_rate_type>` can either be `CALENDAR_DAY` or `STREAM_DAY`.

## Example
Specifying consumption rate type for fixed/direct consumers:

~~~~~~~~yaml
LOAD: 10
CONSUMPTION_RATE_TYPE: CALENDAR_DAY
...
FUELRATE: 10000
CONSUMPTION_RATE_TYPE: STREAM_DAY
~~~~~~~~

Given `CALENDAR_DAY` input the rate will be converted to `STREAM_DAY` when evaluating, and any fuel rate in output
will be converted back again to `CALENDAR_DAY` rate equivalent in the results.

Given `STREAM_DAY` input, and a [REGULARITY](/about/references/keywords/REGULARITY.md) factor of 0.5 (50%), the
interpretation is that the process unit will run at full capacity half of the time. The resulting fuel rate reported
for a fuel consumer will be halved compared to 1 (100%) regularity.
