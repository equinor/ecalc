---
sidebar_position: 8
description: eCalc FAQ
---
# FAQ / Troubleshooting
While running eCalc as a Unix command-line tool, you may come across seemingly incomprehensible error messages.
This page tries to explain some common error messages and proposes how to fix them.

## Indentation errors
In YAML, the indentation is very important and specifies the level in the hierarchy for the input.
If you have the wrong indentation somewhere, you may get both YAML read errors and/or eCalc setup errors.

### Error messages due to YAML read problems
The following error messages are common when you have formatting issues in your YAML file:

~~~~~~~~text
mapping values are not allowed here
~~~~~~~~

~~~~~~~~text
while scanning a simple key in "<setupfile.yml>", line <n>, column <m>
could not find expected ':', line <n>, column <m>
~~~~~~~~

~~~~~~~~text
while parsing a block mapping in <setupfile>, line <n>, column <m>
expected <block end>, but found '<block mapping start>'
~~~~~~~~

### Error messages due to invalid eCalc configuration
The configuration expects a sub-hierarchy of data. After reading YAML, this data sub-hierarchy would be of object type
dictionary (dict) and in some cases contain lists or other objects. If invalid data is input, the error message would
indicate that the type is wrong because it is not a 'dict'/'list' or other type

~~~~~~~~text
None should be instance of 'dict'
~~~~~~~~

~~~~~~~~text
None should be instance of 'list'
~~~~~~~~

### Proposed solution
Check your YAML setup file for correct indentation and correct format of values for each eCalc key.

## Special characters in Unicode
eCalc uses [ruamel.yaml](https://pypi.org/project/ruamel.yaml/) to read the YAML setup files. Some (text) files have an encoding not supported and will thus result in an error message.

One example of this is an unrecognized "[BOM](https://en.wikipedia.org/wiki/Byte_order_mark)" character in "[UTF-8 Unicode](https://nl.wikipedia.org/wiki/UTF-8)".

Error message

~~~~~~~~yaml
while scanning a simple key in "<setupfile.yml>", line <n>, column 1
could not find expected ':', line <n>, column 1
~~~~~~~~

### Proposed solution
Check the encoding of your setupfile (and inputfiles):

~~~~~~~~bash
$ file <setupfile>.yml
~~~~~~~~

If the output of this is not "ASCII text", convert your file to "US-ASCII" using [iconv](https://en.wikipedia.org/wiki/iconv).

Example when `<setupfile>.yml` is of type "UTF-8"

~~~~~~~~bash
$ iconv -f UTF-8 -t US-ASCII//TRANSLIT -o <new_setup_file_name_ascii>.yml <old_setup_file_name_utf-8>.yml
~~~~~~~~

Now try to run again using the new file `<new_setup_file_name_ascii>.yml`.

