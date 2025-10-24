# DCAT-US 3.0 Schema Differences Analysis

This document provides a comprehensive analysis of differences between the three DCAT-US 3.0 schema representations:
1. **Website Documentation** (https://doi-do.github.io/dcat-us/)
2. **SHACL Shapes** (dcat-us_3.0_shacl_shapes.ttl)  
3. **JSON Schema** (dcat_us_3.0.0_schema.json and definitions/)

## Executive Summary

The analysis reveals several categories of discrepancies across the three schema formats, primarily related to data type representations, cardinality constraints, multilingual support, and property requirement levels.

## 1. Data Type and Format Differences

### 1.1 Keyword Property Type Mismatch

**Location Evidence:**
- JSON Schema: `/dcat-us3/jsonschema/definitions/Dataset.json` lines 275-286
- SHACL: `/dcat-us3/dcat-us_3.0_shacl_shapes.ttl` lines 927-940, 1901-1916
- Website: Dataset section, "keyword/tag" property table

**Discrepancy:**
- **JSON Schema**: Defines `keyword` as simple `"type": "string"` (line 284)
- **SHACL**: Defines `keyword` with `sh:or dash:StringOrLangString` allowing both plain strings and array of strings.
- **Website**: Lists Cardinality as 0..n, implying a list.

**Impact:** JSON implementations cannot handle multilingual keywords, contradicting the website's multilingual guidance in Usage Guidelines section. The website goes further, showcasing examples of "keywordMap" showing multilingual support that the schema doesn't define or recognize (not invalid, just ignores).

### 1.2 Multilingual Property Support

**Location Evidence:**
- Website: https://doi-do.github.io/dcat-us/#multilingualism

**Discrepancy:**
Since this is pulled from EU's DCAT-AP, there is an outstanding question of whether this feature is necessary and should be supported for all items.

## 2. Cardinality and Requirement Differences

## 4. Namespace and URI Inconsistencies

### 4.1 Property URI Definitions

**Location Evidence:**
- Website: Namespace table shows standardized URIs
- JSON Schema: Uses `$id` fields for property identification
- SHACL: Uses full URI paths in `sh:path` declarations

**Potential Issues:**
Cross-format references may not always align perfectly, potentially causing interoperability issues between JSON-LD and RDF serializations.

## Mandatory/Required Elements
Why do we now have many required elements on the catalog definition?
Why are we loosening the requirements for a dataset?
Is it useful for ANYONE to have a dataset registered with a title and description, but without a contactPoint, distribution, publisher, or any other information for usage or access?
What does Recommended mean? What is the difference between Recommended and Optional?
There is no longer any nuance without requirements it seems; you cannot require at least one of accessURL or downloadURL for a distribution for example. Why not?

## Field specific Differences

### Optionality in number (arrays)
Catalog Title/description

## Lack of real-world examples
Lots of minute examples, but no "real world" put together use case of a complete, ideal document. How do the pieces fit together? Where do things fit in? Can we get one "complete" example using all features in a single document?

## Ownership and update/edit process

## Website and SHACL mismatch
Dataset describedBy required in SHACL, not on website.
Dataset publisher required in SHACL, not on website.
Organization prefLabel is required in SHACL, not on website.
Activity label is required on the website, not in SHACL.

## JSON Schema, JSON-LD, and SHACL usage



## 5. Controlled Vocabulary References


## 6. Format-Specific Implementation Differences

### 6.1 JSON-LD Context Handling

**Location Evidence:**
- Website: JSON-LD context file reference (dcat-us-3.0.jsonld)
- JSON Schema: Structural validation only
- SHACL: RDF-based validation

**Discrepancy:**
JSON Schema cannot validate semantic correctness that depends on JSON-LD context expansion, while SHACL operates on the expanded RDF graph. This creates a validation gap for JSON implementations.

## 7. Temporal Property Format Differences

**Location Evidence:**
- Website: "Temporal Metadata" section shows multiple XSD date formats
- JSON Schema: May specify single format constraints
- SHACL: Uses XSD datatype constraints

**Discrepancy:**
The website supports multiple temporal formats (`xsd:date`, `xsd:dateTime`, `xsd:gYear`, `xsd:gYearMonth`), but JSON Schema and SHACL may not consistently allow all these variations for temporal properties.

## 8. Class Definition Coverage

### 8.1 Supporting vs Core Classes

**Location Evidence:**
- Website: Distinguishes between core DCAT classes and DCAT-US extensions
- JSON Schema: May have incomplete coverage of supporting classes
- SHACL: Should include shapes for all classes but may have gaps

**Discrepancy:**
Not all classes documented on the website have corresponding JSON Schema definitions or SHACL shapes, particularly for newer DCAT-US 3.0 specific classes.

## Recommendations

### For JSON Schema:
1. Add multilingual support patterns for properties marked as multilingual on the website
2. Include validation for controlled vocabularies where mandated
3. Support multiple temporal formats as documented

### For SHACL Shapes:
1. Ensure all DCAT-US specific properties have corresponding property shapes
2. Add controlled vocabulary constraints using `sh:in` where required by website
3. Verify cardinality constraints match website specifications

### For Website Documentation:
1. Add explicit notes about format-specific implementation limitations
2. Provide clearer guidance on JSON-LD context requirements
3. Include validation examples for each format

## Conclusion

While the three formats serve different purposes (documentation, RDF validation, and JSON validation), better alignment is needed to ensure consistent implementation of DCAT-US 3.0 across different systems and serializations. The most critical issues involve multilingual support and controlled vocabulary enforcement, which could impact data interoperability and compliance.

---

*Analysis completed: $(date)*
*Files analyzed: Website content, SHACL shapes file, JSON Schema definitions*