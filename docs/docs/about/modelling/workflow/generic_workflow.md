---
title: Generic Workflow
sidebar_position: 1
description: Generic workflow 
---

## Simplified Process Flow Diagram
The image below illustrates a simplified process flow diagram for a generic offshore oil and gas facility. Each unit included in this diagram can be modelled with the use of eCalc. 
The [workflow](#workflow) below will outline what is necessary to obtain for each step. In addition, there are some accompanied [explanations](#workflow-explanation) to the workflow.

![](images/simple_facility_pfd.jpg)


## Workflow 

```mermaid
  flowchart TD;
      subgraph ide1 ["`**Required Subsurface Profiles [All in Sm3/d]**`"]
          ide1_A[Oil Produced];
          ide1_B[Gas Produced];
          ide1_C[Water Produced];
          ide1_D[Gas Injected];
          ide1_E[Water Injected];
      end
      subgraph ide2 ["`**Facility Information Needed**`"]

          ide2_A[[Power Generation System]] --> ide2_A_1([Gas Turbines]);
          ide2_A_1 --> ide2_A_2(["`Number of Gas Turbines `"]);
          ide2_A_2 --> ide2_A_3(["`Maximum capacity per generator and spinning reserve`"]);
    
          ide2_B[["Water Injection System"]] --> ide2_B_1(["`Suction Pressure`"]);
          ide2_B_1 --> ide2_B_2(["`Discharge Pressure`"]);
          ide2_B_2 --> ide2_B_3(["`Injected Water Density`"]);
          ide2_B_3 --> ide2_B_4(["`Maximum capacity per pump`"]);
    
          ide2_D[[Gas Compression System]] --> ide2_D_1(["`Export Compressor`"]);
          ide2_D --> ide2_D_1_1(["`Re-Injection Compressor`"]);
          ide2_D_1 --> ide2_D_2(["`Suction Pressure per compressor`"]);
          ide2_D_1_1 -->ide2_D_2
          ide2_D_2 --> ide2_D_3(["`Discharge Pressure per compressor`"]);
          ide2_D_3 --> ide2_D_4(["`Suction Temperature per compressor`"]);
          ide2_C[["Constant Power Loads"]] --> ide2_C_1(["`Base Load`"]);
          ide2_C_1 --> ide2_C_2(["`Oil Export Pumps`"]);
          ide2_C_2 --> ide2_C_3(["`Gas Recompressor`"])
    
          ide2_E[[Additional Emissions]] --> ide2_E_1([Flaring]);
          ide2_E_1 --> ide2_E_2(["`Electrical Submersible Pumps (ESP)`"])
          ide2_E_2 --> ide2_E_3(["`Drilling rigs`"])
      
      end

      subgraph ide3 ["`**Consumer Data Needed**`"]

          ide3_A[[Generator Set]]--> ide3_A_1(["`Fuel vs Power relationship. Linear lines relating fuel and power`"]);
          ide3_A_1 --> ide3_A_2(["`Generating switching. At max capacity of the generator, impose another generate on the existing`"]);
    
          ide3_B[[Compressors]] --> ide3_B_1(["`Variable/single speed drive`"]);
          ide3_B_1 --> ide3_B_2{Available charts?};
          ide3_B_2 -. yes .-> ide3_B_4(["`Use suppliers compressor chart (head vs flow, efficiency vs flow)`"]);
          ide3_B_2  -. no .-> ide3_B_3(["`Use generic chart functionality`"]);
    
          ide3_C[[Water Injectors]] --> ide3_C_1(["`Variable/single speed drive`"]);
          ide3_C_1 --> ide3_C_2{Available charts?};
          ide3_C_2 -. yes .-> ide3_C_4(["`Use suppliers pump chart (head vs flow, efficiency vs flow)`"]);
          ide3_C_2 -. no .-> ide3_C_3(["`Generate synthetic charts using expected head and flow ranges`"]);

      end

      subgraph ide4 ["`**Validation**`"]

          ide4_A{"Invalid data?"} 

          ide4_A -. yes .-> ide4_A_1{"`Invalid Compressors?`"};
          ide4_A_1 -. yes .-> ide4_A_1_1(["`Either head or rate is too high`"]);
          ide4_A_1_1 --> ide4_A_1_2(["`Plot operational points and adjust charts to fit historical data`"]);
    
          ide4_A -. yes .-> ide4_A_3{"`Invalid Pumps?`"};
          ide4_A_3 -. yes .-> ide4_A_3_1(["`Either head or rate is too high`"]);
          ide4_A_3_1 --> ide4_A_3_2(["`Plot operational points and adjust charts to fit historical data`"]);
    
          ide4_A -. yes .-> ide4_A_4{"`Invalid Generator Set?`"};
          ide4_A_4 -. yes .-> ide4_A_4_1(["`Check maximum and minimum facility power consumption values are within the range of the specified generator set`"]);
          ide4_A_4_1 --> ide4_A_4_2(["`Adjust generator set`"]);

      end

      subgraph ide5 ["`Calibration`"]

          ide5_A["`Calibration`"] --> ide5_A_1(["`Compare measured power against eCalc power`"]) ;
          ide5_A_1 --> ide5_A_2{"`Do they correlate`"}
          ide5_A_2 -. yes .-> ide5_A_3_1{"`Are all points valid?`"};
          ide5_A_3_1 -. yes .-> ide5_A_3_2(["`No further calibration needed`"])
          ide5_A_2 -. no .-> ide5_A_2_1(["`Consider using POWERLOSSFACTOR to adjust modelled to measured power`"])
          ide5_A_2_1 --> ide5_A_3_1
          ide5_A_4_1(["`Plot operational points on the same figure as the performance chart`"]) --> ide5_A_4_2(["`Alter the head vs flow curves (using fan law theory)`"])
          ide5_A_4_2 --> ide5_A_1
          ide5_A_3_1 -. no .-> ide5_A_4_1
      end
      
      ide1 ~~~ ide2
      ide2 ~~~ ide3
      ide3 ~~~ ide4
      ide4 ~~~ ide5
```

## Workflow Explanation

### Required Subsurface Profiles

All subsurface profiles must be in Sm<sup>3</sup>/day. This data must be inputted as a `TIME-SERIES` and references to how it is used in the facility or by a relevant consumer.

### Facility Information

#### Constant Power Loads

To simplify certain models, there are some common assumptions made. Here are some examples:

- **Base Load**: As eCalc™ is not simulating the whole facility there are often energy consumers that are not modelled. 
Typically these energy consumers relate to things such as the energy consumption of living quarters and are often constant loads.
These smaller constant loads are then grouped into a larger term, called the "baseload". This is assumed to be constant and independent of the production rate of the facility.
- **Recompressor**: The main function of a recompressor is to compressor gas from separator pressures back up to the inlet separator pressure.
These compressors are often smaller and have little fluctuation in their load.
Thus, to simplify modelling, these recompressors are often modelled as constant loads. And at times, are included within the facility's base load
- **Oil Export Pumps**: As eCalc™ does not model oil pumps, these are often modelled as constant loads or modelled with a table (that relates oil rate to power consumption). The method in which they are modelled depends from facility to facility 

#### Additional Information

Any emissions that do not fall within the defined categories can still be considered for a given platform. For example, if there are drilling activities, an additional fuel type can be specified and related to the fuel consumption of a drilling rig. 

### Consumer Information

#### Generator Set

As eCalc™ does not indepthly model gas turbine generators, alternative methods are used. 
Here, fuel consumed and power generated is related in tabular form. These are typically linear relationships, and if more than one generator is used, "generator switching" is modelled by adding another generator curve on top of the existing.

This means that the facility will operate in the most efficient manner, i.e. meaning that if one generator will satisfy the power demand, only one generator will always be used. 

#### Compressor Curves

eCalc™ has generic compressor curve functionality which can be used when compressor curves are not available. 
However, if a manufactor compressor chart is available, it is always recommended to use this over a generic chart. 
The generic compressor curves, use the assumption of constant polytropic efficiency, which is only a good assumption if the compressor is running near the design points. 


### Validation

Checking whether an eCalc™ model is valid or not, is an essential task. If a model is not valid, this means that input requirements set by the user are not being fulfilled, or that some consumers are giving unrealistic solutions.

Validity can be checked by consumer, and there are often specific reasons why certain consumers are invalid. For example:

- **Compressors and Pumps**: It is common that either too high a head or rate value is specified. This means that the invalid point is outside the limits of the performance chart. To determine the issue, it is recommended that the operational points (Head, and actual flowrate) are plotted together with the chart.
- **Generator Set**: The most common issue here is that the amount of power required is higher than the maximum value in the utilised genset. 

### Calibration

The term calibration in eCalc™ often refers to the history matching of the facility. Essentially, real operational data is compared against the eCalc™ model results. If they do not correlate various changes are made to the model.

The main workflow with this would be to match every individual consumer, e.g. each pump and compressor. After that, it is the recommended to compare on the facility level (e.g. total power consumed or total fuel used), then various adjustments can be made.
These adjustments can mean changes to the base load, shifting the compressor curves, or simply by using a [POWERLOSSFACTOR](/about/references/keywords/POWERLOSSFACTOR.md).