# !include
## Description

You can use `!include` to separate your model into several files. `!include`
can be used as value in a `KEY: VALUE` mapping, or as a value in a list.

## Format
~~~~~~~~yaml
!include <some_yaml_file.yaml>
~~~~~~~~

:::tip
You can use `ecalc show yaml <model_file>` to see the read yaml with `!include` processed.

New in v7.2.
:::
## Example 1 - include map/object into list item
`!include` can be used to insert a map/object as a single list element

~~~~~~~~yaml title="main.yaml" {2}
 INSTALLATIONS:
   - !include installationA.yaml
   - NAME: installationB
     ...
~~~~~~~~

~~~~~~~~yaml title="installationA.yaml"
    NAME: installationA
    ...

~~~~~~~~

This is the same as

~~~~~~~~yaml title="main.yaml" {2,3}
     INSTALLATIONS:
       - NAME: installationA
         ...
       - NAME: installationB
         ...

~~~~~~~~

## Example 2 - include map/object into object value
`!include` can be used to insert a map/object as a value in a `KEY: VALUE` mapping

~~~~~~~~yaml title="main.yaml" {5}
 INSTALLATIONS:
   - NAME: installationA
     FUELCONSUMERS:
       - NAME: consumerB
         ENERGY_USAGE_MODEL: !include consumerB.yaml
~~~~~~~~

~~~~~~~~yaml title="consumerB.yaml"
    TYPE: COMPRESSOR
    ...

~~~~~~~~

This is the same as

~~~~~~~~yaml title="main.yaml" {6,7}
     INSTALLATIONS:
       - NAME: installationA
         FUELCONSUMERS:
           - NAME: consumerB
             ENERGY_USAGE_MODEL:
               TYPE: COMPRESSOR
               ...

~~~~~~~~

## Example 3 - include list into object value
`!include` can be used to insert a list as a value in a `KEY: VALUE` mapping

~~~~~~~~yaml title="main.yaml" {1}
INSTALLATIONS: !include installations.yaml

~~~~~~~~


~~~~~~~~yaml title="installations.yaml"
    - NAME: installationA
      ...
    - NAME: installationB
      ...

~~~~~~~~

This is the same as

~~~~~~~~yaml title="main.yaml" {2-5}
     INSTALLATIONS:
       - NAME: installationA
         ...
       - NAME: installationB
         ...
~~~~~~~~

