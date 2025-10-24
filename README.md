# dcat-us3-tools
A place to store DCAT-US3 tools: exploration, testing, definition, examples, and (possibly) transformation services/definition.

Documentation and summary information can be found in the [DCAT-US3 Transition](https://docs.google.com/document/d/1ALjlkNEFyatDA3OQWbw7CiB5exGin6-N-SO42gfG_R4/edit?tab=t.0#heading=h.2u14859cscyk) document.

## Overview of tools

### dcat-us1.1
This is meant to represent the "old" way of DCAT-US1.1.
This has the JSON Schema definition (catalog.json and dataset.json).
It has a script called `validate_examples.py`, which will validate everything in the examples folder.

### dcat-us3
This is meant to represent the "new" way of DCAT-US3.
There are a number of things in this repository, as this is meant to explore this new use case. We have the examples folder broken down into good and bad examples, which are meant to validate certain use cases.
We have a jsonschema folder, which houses the jsonschema definition as provided by the infopolicy repo of the documentation of DCAT-US3. Since this schema doesn't have a defining "starting" point, and only defines objects, a file called `dcat-us3.0-expanded-schema.json` was used to collate all the schemas and place them into a single definitions file. This was done with the combine_schema_manual.py script.

We have a JSON-LD representation and a SHACL ttl definition of the shape of the DCAT-US3 objects. These are also taken from the upstream [infopolicy repo](https://github.com/infopolicy/dcat-us).

Then we have 2 scripts, one for validating the examples with the JSON schema and another with the SHACL shape definition. The goal is to be able to validate with either; that may not be possible without edits.

## Installation

This project uses poetry to install and manage python dependencies. Please see
[poetry documentation](https://python-poetry.org/docs/) for more information.
