---
title: Fixed speed pressure control
sidebar_position: 3
description: Introduction to fixed speed pressure control
---

# Fixed speed pressure control

Generally, the work performed by a compressor train can be reduced/increased by changing the rotational speed
of the compressor train shaft. In some cases there is a need to reduce the discharge pressure from a compressor
train without changing the rotational speed of the shaft. Examples can be:

- The compressor train only operates at one speed (a [SINGLE_SPEED_COMPRESSOR_TRAIN](../compressor_models_types/single_speed_compressor_train_model.md)),
  and the given rate and suction pressure gives a too high discharge pressure.
- The compressor train is a [VARIABLE_SPEED_COMPRESSOR_TRAIN](../compressor_models_types/variable_speed_compressor_train_model.md),
  but it already operates at the minimum speed, and still the discharge pressure is too high.
- The compressor train is a [VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES](../compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md) 
  required to meet an export pressure, before compressing gas further for injection. Here the
  rotational speed required to bring the gas from inlet pressure to export pressure may be higher than the speed
  required to bring the gas from export pressure to discharge pressure. Hence, the rotational speed giving 
  the correct export pressure will give a too high discharge pressure.  

In a situation where the rotational speed of the shaft can not be varied here are only two degrees of freedom. 
This means that if you give the suction pressure and the flow rate as input, the discharge pressure is decided by those 
two inputs. Similarly, if you give the rate and the discharge pressure as input, the suction pressure is decided by 
those two inputs. Hence, to calculate the energy usage for a given rate, suction pressure and discharge pressure, a
method for fixed speed pressure control must be defined. This can be done by a choke valve upstream or downstream 
of the compressor train, or by recirculating fluid inside the compressor train. 

Currently, there are two options for choking the pressure in eCalc:

- UPSTREAM_CHOKE: The suction pressure is reduced such that the resulting suction pressure after choking together 
  with the given speed results in the required discharge pressure.
- DOWNSTREAM_CHOKE: The pressure is choked to the required discharge pressure after the compressor train.

The head in a compressor is reduced when the rate is increased. Hence, recirculation can reduce the 
discharge pressure for a single speed compressor, as shown in the figure below.

![](make_recirculation_pressure_control_plot.png)

For an actual volume rate of 1882 am3/hr, the head is
93 kJ/kg (blue dashed lines). If this head leads to a too large discharge pressure, it can be reduced by recirculation
using the anti-surge valve. As the actual flow rate through the compressor increases, the head is also reduced,
meaning that a higher actual flow rate leads to a lower discharge pressure. By e.g. increasing the actual volume rate
to 2322 am3/hr (by recirculating 440 am3/hr through the ASV), the head is reduced to about 81.3 kJ/kg (red dashed lines)
, in turn leading to a lower discharge pressure. The head can be reduced further down to 42.5 kJ/kg at the maximum flow
rate (3201 am3/hr) for the compressor (yellow dashed lines). The difference between the flow rate entering the
compressor train and the maximum flow rate for the compressor gives the amount of additional volume that can be
recirculated through the compressor - the available capacity.

With only one compressor stage or only one recirculation loop (common asv over the entire compressor train), 
a unique solution to how much volume to recirculate is available. With individual ASVs for each compressor stage, 
the problem is under determined, and there are multiple possible solutions. Therefore, some modelling choices must 
be done. There are currently two options available in eCalc: to increase the flow rate in each compressor stage 
with the same fraction of the available capacity, or to keep the pressure ratio (discharge pressure/suction pressure) 
over each compressor stage constant.

All together this mean that there are three options for fixed speed pressure control involving 
recirculation in eCalc: 

- INDIVIDUAL_ASV_PRESSURE: The pressure ratio (discharge pressure/suction pressure) over each compressor stage is constant.
- INDIVIDUAL_ASV_RATE: The flow rate through each compressor stage is increased with the same fraction of the available capacity in that stage.
- COMMON_ASV: The same volume is recirculated through the entire compressor train.
