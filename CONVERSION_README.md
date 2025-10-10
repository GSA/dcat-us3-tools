# DCAT-US 1.1 to 3.0 Conversion Tool

This repository contains a Python script that converts DCAT-US 1.1 JSON files to DCAT-US 3.0 JSON-LD format.

## Overview

The `convert_dcat_us.py` script provides automated transformation of DCAT-US metadata from version 1.1 to version 3.0, using a comprehensive mapping approach with detailed transformation rules.

## Key Features

- **Mapping-based transformation**: Uses a comprehensive mapping object to transform property names from 1.1 to 3.0 format
- **JSON-LD compliance**: Outputs properly structured JSON-LD with correct `@context` and namespaces
- **SHACL validation ready**: Converted files pass DCAT-US 3.0 SHACL validation
- **Batch processing**: Can process individual files or entire directories
- **Detailed logging**: Provides warnings for unmapped properties and transformation issues

## Usage

### Basic Usage

Convert a single file:
```bash
python3 convert_dcat_us.py input.json -o output-v3.jsonld
```

Convert all JSON files in a directory:
```bash
python3 convert_dcat_us.py input_directory/ --batch -o output_directory/
```

### Command Line Arguments

- `input`: Input DCAT-US 1.1 JSON file or directory containing JSON files
- `-o, --output`: Output file or directory (defaults to input location with `-v3.jsonld` suffix)
- `--batch`: Process all JSON files in the input directory

## Key Transformations

### 1. Context and Namespaces

**DCAT-US 1.1:**
```json
{
  "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld"
}
```

**DCAT-US 3.0:**
```json
{
  "@context": {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "vcard": "http://www.w3.org/2006/vcard/ns#",
    "dcat-us": "http://data.resources.gov/ontology/dcat-us#",
    "schema": "https://schema.org/",
    "org": "http://www.w3.org/ns/org#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#"
  }
}
```

### 2. Property Mappings

| DCAT-US 1.1 | DCAT-US 3.0 | Notes |
|--------------|-------------|-------|
| `title` | `dcterms:title` | Direct mapping |
| `description` | `dcterms:description` | Direct mapping |
| `publisher` | `dcterms:publisher` | Requires structural transformation |
| `contactPoint` | `dcat:contactPoint` | Requires vCard structure |
| `distribution` | `dcat:distribution` | Requires Distribution structure |
| `accessLevel` | `dcat-us:accessLevel` | US-specific extension |
| `bureauCode` | `dcat-us:bureauCode` | US-specific extension |
| `programCode` | `dcat-us:programCode` | US-specific extension |

### 3. Structural Transformations

#### Contact Points
**1.1 Format:**
```json
{
  "contactPoint": {
    "fn": "John Doe",
    "hasEmail": "john.doe@agency.gov"
  }
}
```

**3.0 Format:**
```json
{
  "dcat:contactPoint": {
    "@type": "vcard:Contact",
    "vcard:fn": "John Doe",
    "vcard:hasEmail": {"@id": "mailto:john.doe@agency.gov"}
  }
}
```

#### Publishers
**1.1 Format:**
```json
{
  "publisher": {
    "name": "Department of Example",
    "subOrganizationOf": {"name": "U.S. Government"}
  }
}
```

**3.0 Format:**
```json
{
  "dcterms:publisher": {
    "@type": "org:Organization",
    "foaf:name": "Department of Example",
    "skos:prefLabel": "Department of Example",
    "org:subOrganizationOf": {
      "@type": "org:Organization",
      "foaf:name": "U.S. Government",
      "skos:prefLabel": "U.S. Government"
    }
  }
}
```

#### Distributions
**1.1 Format:**
```json
{
  "distribution": [{
    "accessURL": "https://example.gov/data.csv"
  }]
}
```

**3.0 Format:**
```json
{
  "dcat:distribution": [{
    "@type": "dcat:Distribution",
    "dcat:accessURL": {"@id": "https://example.gov/data.csv"},
    "dcterms:license": {"@id": "https://creativecommons.org/publicdomain/zero/1.0/"}
  }]
}
```

### 4. Additional Transformations

- **URLs as IRIs**: All URLs (accessURL, downloadURL, etc.) are converted to IRI objects with `@id`
- **Date formatting**: Dates are properly typed with XSD datatypes where applicable
- **Required properties**: Adds required properties like licenses and organization labels where missing
- **Spatial data**: Geographic references converted to dcterms:Location resources

## Complex Transformation Handling

The script handles several complex scenarios that require more than simple key mapping:

### 1. Frequency vs. Modified Date
DCAT-US 1.1 sometimes uses the `modified` field for frequency expressions (e.g., "R/P1W" for weekly). The script:
- Detects frequency patterns in date fields
- Issues warnings for problematic date values
- Skips invalid date formats to prevent validation errors

### 2. Required Fields
DCAT-US 3.0 SHACL shapes require certain fields that may be missing in 1.1 data:
- Adds default catalog publisher if missing
- Adds default distribution license
- Adds required organization labels (`skos:prefLabel`)

### 3. IRI Requirements
Many properties that were literals in 1.1 must be IRIs in 3.0:
- URLs become IRI objects: `"url"` → `{"@id": "url"}`
- References become IRI objects: `"reference"` → `{"@id": "reference"}`

## Validation

The converted files are designed to pass DCAT-US 3.0 SHACL validation. You can validate converted files using:

```bash
python3 dcat-us3/validate_shacl.py converted-file.jsonld
```

## Examples

The script has been tested on the included DCAT-US 1.1 examples:
- `dcat-us1.1/examples/dcatus.json` → `dcat-us3/examples/dcatus-v3.jsonld`
- `dcat-us1.1/examples/dcatus_2.json` → `dcat-us3/examples/dcatus_2-v3.jsonld`

Both converted examples pass DCAT-US 3.0 SHACL validation.

## Notes and Warnings

1. **Duration/Frequency Handling**: The script warns when `modified` dates contain frequency expressions (R/P patterns) and skips them since they're not valid dates
2. **Unmapped Properties**: The script prints warnings for any properties that don't have explicit mappings
3. **Default Values**: Some required fields are populated with sensible defaults when missing from source data
4. **Manual Review**: While the script handles most transformations automatically, complex domain-specific properties may require manual review

## Dependencies

- Python 3.6+
- No additional dependencies required for basic conversion
- For validation: `pyshacl`, `rdflib` (already in project dependencies)