# DCAT-US 3.0 vs DCAT-US 1.1 Dataset Schema Comparison

This compares the JSON Schema definitions, apples to apples.
If JSON schema is no longer used in favor of SHACL, some of these representations
are incorrect (for example, keyword).

| Level | Field (DCAT-US 3.0) | Equivalent Field (DCAT-US 1.1) | Notes |
|-------|---------------------|--------------------------------|-------|
| **Schema Metadata** |
| Root | `$schema` | `$schema` | 3.0 uses draft-07, 1.1 uses draft/2020-12 |
| Root | `title` | `title` | Both present, same purpose |
| Root | `type` | `type` | Both "object" |
| **Core Properties** |
| Dataset | `@id` | *(none)* | **NEW in 3.0** - IRI identifier for JSON-LD |
| Dataset | `@type` | `@type` | 3.0 default "Dataset", 1.1 const "dcat:Dataset" |
| Dataset | `title` | `title` | Same - required string in both |
| Dataset | `publisher` | `publisher` | 3.0: Organization object/IRI, 1.1: organization object |
| Dataset | `identifier` | `identifier` | **CHANGED**: 3.0 array of strings/null, 1.1 single required string |
| Dataset | `keyword` | `keyword` | **CHANGED**: 3.0 single string/null, 1.1 required array of strings (yes, you are reading that correctly; DCAT-US3 keyword field only takes a single string according to the schema)|
| Dataset | `contactPoint` | `contactPoint` | **CHANGED**: 3.0 array of Kind objects, 1.1 single vCard object |
| **New Properties in DCAT-US 3.0** |
| Dataset | `otherIdentifier` | *(none)* | **NEW** - Array of Identifier objects/IRIs |
| Dataset | `sample` | *(none)* | **NEW** - Array of Distribution samples |
| Dataset | `status` | *(none)* | **NEW** - Lifecycle status as Concept |
| Dataset | `supportedSchema` | *(none)* | **NEW** - Supported schema reference |
| Dataset | `versionNotes` | *(none)* | **NEW** - Version notes string |
| Dataset | `first` | *(none)* | **NEW** - First item in sequence |
| Dataset | `hasCurrentVersion` | *(none)* | **NEW** - Current version reference |
| Dataset | `hasVersion` | *(none)* | **NEW** - Array of version references |
| Dataset | `inSeries` | *(none)* | **NEW** - Dataset series membership |
| Dataset | `keywordMap` | *(none)* | **NEW** - Language map for keywords |
| Dataset | `previousVersion` | *(none)* | **NEW** - Previous version reference |
| Dataset | `qualifiedRelation` | *(none)* | **NEW** - Array of qualified relationships |
| Dataset | `spatialResolutionInMeters` | *(none)* | **NEW** - Spatial resolution |
| Dataset | `temporalResolution` | *(none)* | **NEW** - Temporal resolution |
| Dataset | `version` | *(none)* | **NEW** - Version indicator string |
| Dataset | `geographicBoundingBox` | *(none)* | **NEW** - Array of bounding box objects |
| Dataset | `liabilityStatement` | *(none)* | **NEW** - Liability statement |
| Dataset | `metadataDistribution` | *(none)* | **NEW** - Metadata distribution array |
| Dataset | `purpose` | *(none)* | **NEW** - Purpose string |
| Dataset | `purposeMap` | *(none)* | **NEW** - Language map for purpose |
| Dataset | `contributor` | *(none)* | **NEW** - Array of contributing agents |
| Dataset | `created` | *(none)* | **NEW** - Creation date |
| Dataset | `creator` | *(none)* | **NEW** - Creator entity |
| Dataset | `descriptionMap` | *(none)* | **NEW** - Language map for description |
| Dataset | `hasPart` | *(none)* | **NEW** - Array of part datasets |
| Dataset | `isReferencedBy` | *(none)* | **NEW** - Array of referencing resources |
| Dataset | `provenance` | *(none)* | **NEW** - Array of provenance statements |
| Dataset | `relation` | *(none)* | **NEW** - Array of related resources |
| Dataset | `replaces` | *(none)* | **NEW** - Array of replaced datasets |
| Dataset | `rightsHolder` | *(none)* | **NEW** - Array of rights holders |
| Dataset | `source` | *(none)* | **NEW** - Array of source resources |
| Dataset | `subject` | *(none)* | **NEW** - Array of subject concepts |
| Dataset | `titleMap` | *(none)* | **NEW** - Language map for title |
| Dataset | `category` | *(none)* | **NEW** - Array of category concepts |
| Dataset | `hasQualityMeasurement` | *(none)* | **NEW** - Array of quality measurements |
| Dataset | `page` | *(none)* | **NEW** - Array of documentation pages |
| Dataset | `qualifiedAttribution` | *(none)* | **NEW** - Array of qualified attributions |
| Dataset | `wasAttributedTo` | *(none)* | **NEW** - Array of attribution agents |
| Dataset | `wasGeneratedBy` | *(none)* | **NEW** - Array of generating activities |
| Dataset | `wasUsedBy` | *(none)* | **NEW** - Array of using activities |
| Dataset | `image` | *(none)* | **NEW** - Array of thumbnail images |
| Dataset | `scopeNote` | *(none)* | **NEW** - Usage note string |
| Dataset | `scopeNoteMap` | *(none)* | **NEW** - Language map for usage notes |
| **Transformed Properties** |
| Dataset | `accessRights` | `accessLevel` | **CHANGED**: 3.0 RightsStatement object, 1.1 enum (public/restricted/non-public) |
| Dataset | `rights` | `rights` | **CHANGED**: 3.0 RightsStatement object/IRI, 1.1 string max 255 chars |
| Dataset | `accrualPeriodicity` | `accrualPeriodicity` | **CHANGED**: 3.0 Frequency object/IRI, 1.1 regex patterns |
| Dataset | `conformsTo` | `conformsTo` | **CHANGED**: 3.0 array of Standard objects, 1.1 single URI |
| Dataset | `describedBy` | `describedBy` | **CHANGED**: 3.0 Distribution object/IRI, 1.1 URI string |
| Dataset | `landingPage` | `landingPage` | **CHANGED**: 3.0 Document object/IRI, 1.1 URI string |
| Dataset | `issued` | `issued` | **CHANGED**: 3.0 flexible date formats, 1.1 regex pattern |
| Dataset | `language` | `language` | **CHANGED**: 3.0 array of LinguisticSystem objects, 1.1 array of language codes |
| Dataset | `spatial` | `spatial` | **CHANGED**: 3.0 array of Location objects, 1.1 string or GeoJSON |
| Dataset | `temporal` | `temporal` | **CHANGED**: 3.0 array of PeriodOfTime objects, 1.1 string patterns |
| Dataset | `theme` | `theme` | **CHANGED**: 3.0 array of Concept objects, 1.1 array of strings |
| **Distribution Properties** |
| Distribution | `@id` | *(none)* | **NEW in 3.0** - IRI identifier for JSON-LD |
| Distribution | `@type` | `@type` | 3.0 default "Distribution", 1.1 const "dcat:Distribution" |
| Distribution | `title` | `title` | Same - optional string, but 1.1 has minLength validation |
| Distribution | `downloadURL` | `downloadURL` | **CHANGED**: 3.0 Resource object/IRI, 1.1 URI string |
| Distribution | `accessURL` | `accessURL` | **CHANGED**: 3.0 Resource object/IRI, 1.1 URI string |
| Distribution | `mediaType` | `mediaType` | **CHANGED**: 3.0 MediaType object/IRI, 1.1 string with regex |
| Distribution | `format` | `format` | **CHANGED**: 3.0 MediaType object/IRI, 1.1 string |
| Distribution | `conformsTo` | `conformsTo` | **CHANGED**: 3.0 array of Standard objects, 1.1 single URI |
| Distribution | `describedBy` | `describedBy` | **CHANGED**: 3.0 Distribution object/IRI, 1.1 URI string |
| **New Distribution Properties in DCAT-US 3.0** |
| Distribution | `representationTechnique` | *(none)* | **NEW** - Concept for spatial representation type |
| Distribution | `status` | *(none)* | **NEW** - Lifecycle status as Concept |
| Distribution | `characterEncoding` | *(none)* | **NEW** - Array of character encoding strings |
| Distribution | `accessService` | *(none)* | **NEW** - Array of DataService objects |
| Distribution | `byteSize` | *(none)* | **NEW** - File size in bytes as string |
| Distribution | `compressFormat` | *(none)* | **NEW** - Compression format as MediaType |
| Distribution | `packageFormat` | *(none)* | **NEW** - Packaging format as MediaType |
| Distribution | `spatialResolutionInMeters` | *(none)* | **NEW** - Spatial resolution string |
| Distribution | `temporalResolution` | *(none)* | **NEW** - Temporal resolution string |
| Distribution | `availability` | *(none)* | **NEW** - Availability as Concept |
| Distribution | `accessRestriction` | *(none)* | **NEW** - Array of AccessRestriction objects |
| Distribution | `cuiRestriction` | *(none)* | **NEW** - CUIRestriction object |
| Distribution | `useRestriction` | *(none)* | **NEW** - Array of UseRestriction objects |
| Distribution | `accessRights` | *(none)* | **NEW** - RightsStatement object |
| Distribution | `descriptionMap` | *(none)* | **NEW** - Language map for description |
| Distribution | `identifier` | *(none)* | **NEW** - Array of identifier strings |
| Distribution | `issued` | *(none)* | **NEW** - Release date with flexible formats |
| Distribution | `language` | *(none)* | **NEW** - Array of LinguisticSystem objects |
| Distribution | `license` | *(none)* | **NEW** - LicenseDocument object |
| Distribution | `modified` | *(none)* | **NEW** - Last modified date |
| Distribution | `rights` | *(none)* | **NEW** - RightsStatement object |
| Distribution | `titleMap` | *(none)* | **NEW** - Language map for title |
| Distribution | `hasQualityMeasurement` | *(none)* | **NEW** - Array of QualityMeasurement objects |
| Distribution | `page` | *(none)* | **NEW** - Array of documentation pages |
| Distribution | `image` | *(none)* | **NEW** - Array of thumbnail images |
| Distribution | `checksum` | *(none)* | **NEW** - Checksum object for verification |
| **Distribution Properties Removed in DCAT-US 3.0** |
| Distribution | *(none)* | `describedByType` | **REMOVED** - Media type for data dictionary |
| **Distribution Required Fields** |
| Distribution | Required: 0 fields | Required: 0 fields (conditional) | Both have no required fields, but 1.1 has conditional requirement |
| Distribution | *(conditional)* | Required when `downloadURL` present: `mediaType` | **REMOVED** - 3.0 removes conditional requirement |
| **Properties Removed in DCAT-US 3.0** |
| Dataset | *(none)* | `bureauCode` | **REMOVED** - Federal bureau codes array |
| Dataset | *(none)* | `describedByType` | **REMOVED** - Media type for data dictionary |
| Dataset | *(none)* | `dataQuality` | **REMOVED** - Boolean for quality guidelines |
| Dataset | *(none)* | `primaryITInvestmentUII` | **REMOVED** - IT investment identifier |
| Dataset | *(none)* | `programCode` | **REMOVED** - Federal program codes array |
| Dataset | *(none)* | `references` | **REMOVED** - Related documents array |
| Dataset | *(none)* | `systemOfRecords` | **REMOVED** - Privacy Act system reference |
| Dataset | *(none)* | `isPartOf` | **REMOVED** - Collection membership string |
| **Required Fields** |
| Dataset | Required: 3 fields | Required: 8 fields | **REDUCED**: 3.0 requires only title, description, publisher |
| Dataset | Required: `description` | Required: `description` | Same requirement |
| Dataset | Required: `publisher` | Required: `publisher` | Same requirement |
| Dataset | Required: `title` | Required: `title` | Same requirement |
| Dataset | *(not required)* | Required: `keyword` | **REMOVED** from required |
| Dataset | *(not required)* | Required: `modified` | **REMOVED** from required |
| Dataset | *(not required)* | Required: `contactPoint` | **REMOVED** from required |
| Dataset | *(not required)* | Required: `identifier` | **REMOVED** from required |
| Dataset | *(not required)* | Required: `accessLevel` | **REMOVED** from required |
| **Validation Changes** |
| Dataset | Flexible date formats | Complex regex patterns | 3.0 uses standard formats (date, date-time, YYYY, YYYY-MM) |
| Dataset | IRI format validation | URI format validation | 3.0 uses IRI, 1.1 uses URI |
| Dataset | Object references | Direct validation | 3.0 allows inline objects or IRI references |
| Dataset | Language maps | Direct strings | 3.0 adds internationalization support |
| **Architectural Differences** |
| Root | Object-based schema | Property-based schema | 3.0 uses $ref to definitions extensively |
| Root | Semantic web aligned | Federal data focused | 3.0 more RDF/linked data oriented |
| Root | Flexible validation | Strict validation | 3.0 more permissive, 1.1 more restrictive |
| Root | International scope | US Federal scope | 3.0 designed for broader use |

## Summary Statistics

### Dataset Schema
- **DCAT-US 3.0**: 65+ properties, 3 required fields
- **DCAT-US 1.1**: ~30 properties, 8 required fields  
- **New in 3.0**: 40+ new properties
- **Removed in 3.0**: 9 properties specific to US federal requirements
- **Transformed**: 12 properties with significant structural changes

### Distribution Schema
- **DCAT-US 3.0**: 30+ properties, 0 required fields
- **DCAT-US 1.1**: 9 properties, 0 required fields (with conditional requirement)
- **New in 3.0**: 25+ new properties
- **Removed in 3.0**: 1 property (`describedByType`)
- **Transformed**: 6 properties with significant structural changes

### Overall Evolution
- **Schema Evolution**: From federal-specific to international semantic web standard
- **Flexibility**: DCAT-US 3.0 removes most validation constraints and conditional requirements
- **Semantic Web**: Extensive use of object references and structured data types
- **Internationalization**: Language maps throughout for multilingual support