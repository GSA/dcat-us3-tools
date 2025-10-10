#!/usr/bin/env python3
"""
DCAT-US 1.1 to 3.0 Converter Script

This script converts DCAT-US 1.1 JSON files to DCAT-US 3.0 JSON-LD format.
The conversion is based on a mapping object that transforms property names 
and structures according to the new schema requirements.

Key transformations:
1. Update @context to use proper namespaces
2. Transform property names using dcterms: and dcat: prefixes
3. Restructure contact points and publishers using proper object types
4. Handle complex nested structures with appropriate transformations
"""

import json
import argparse
import os
from typing import Dict, Any, List, Union
from datetime import datetime


class DCATUSConverter:
    """Converts DCAT-US 1.1 format to DCAT-US 3.0 JSON-LD format."""
    
    def __init__(self):
        """Initialize the converter with mapping configurations."""
        
        # Define the new DCAT-US 3.0 context
        self.dcat_us_3_context = {
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
        
        # Catalog-level property mappings (1.1 -> 3.0)
        self.catalog_mapping = {
            # Direct mappings - properties that only need prefix changes
            "conformsTo": "dcterms:conformsTo",
            "describedBy": "dcat-us:describedBy",
            "dataset": "dcat:dataset",
            "title": "dcterms:title",
            "description": "dcterms:description",
            "issued": "dcterms:issued",
            "modified": "dcterms:modified",
            "language": "dcterms:language",
            "license": "dcterms:license",
            "rights": "dcterms:rights",
            "spatial": "dcterms:spatial",
            "temporal": "dcterms:temporal",
            
            # Properties that need structural transformation (handled separately)
            "publisher": "dcterms:publisher",  # Needs foaf:Organization structure
            "contactPoint": "dcat:contactPoint",  # Needs vcard structure
        }
        
        # Dataset-level property mappings (1.1 -> 3.0)
        self.dataset_mapping = {
            # Direct mappings
            "title": "dcterms:title",
            "description": "dcterms:description",
            "keyword": "dcat:keyword",
            "modified": "dcterms:modified",
            "issued": "dcterms:issued",
            "identifier": "dcterms:identifier",
            "accessLevel": "dcat-us:accessLevel",
            "rights": "dcterms:rights",
            "license": "dcterms:license",
            "spatial": "dcterms:spatial",
            "temporal": "dcterms:temporal",
            "accrualPeriodicity": "dcterms:accrualPeriodicity",
            "conformsTo": "dcterms:conformsTo",
            "dataQuality": "dqv:hasQualityMeasurement",
            "theme": "dcat:theme",
            "references": "dcterms:references",
            "isPartOf": "dcterms:isPartOf",
            "landingPage": "dcat:landingPage",
            "language": "dcterms:language",
            
            # Properties with US-specific extensions
            "bureauCode": "dcat-us:bureauCode",
            "programCode": "dcat-us:programCode",
            "primaryITInvestmentUII": "dcat-us:primaryITInvestmentUII",
            "systemOfRecords": "dcat-us:systemOfRecords",
            "dataStandard": "dcat-us:dataStandard",
            
            # Properties that need structural transformation
            "describedBy": "dcat-us:describedBy",  # Needs @id structure
            "publisher": "dcterms:publisher",  # Needs foaf:Organization structure
            "contactPoint": "dcat:contactPoint",  # Needs vcard structure
            "distribution": "dcat:distribution",  # Needs dcat:Distribution structure
        }
        
        # Distribution-level property mappings
        self.distribution_mapping = {
            "accessURL": "dcat:accessURL",
            "downloadURL": "dcat:downloadURL",
            "mediaType": "dcat:mediaType",
            "format": "dcterms:format",
            "title": "dcterms:title",
            "description": "dcterms:description",
            "conformsTo": "dcterms:conformsTo",
            "describedBy": "dcat-us:describedBy",
        }
    
    def transform_contact_point(self, contact_point: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform contactPoint from DCAT-US 1.1 vcard format to DCAT-US 3.0 format.
        
        In 1.1: {"fn": "Name", "hasEmail": "mailto:email@domain.com"}
        In 3.0: {"@type": "vcard:Contact", "vcard:fn": "Name", "vcard:hasEmail": {"@id": "mailto:email@domain.com"}}
        """
        transformed = {"@type": "vcard:Contact"}
        
        if "fn" in contact_point:
            transformed["vcard:fn"] = contact_point["fn"]
        
        if "hasEmail" in contact_point:
            # In 3.0, email should be an object with @id
            email = contact_point["hasEmail"]
            if not email.startswith("mailto:"):
                email = f"mailto:{email}"
            transformed["vcard:hasEmail"] = {"@id": email}
        
        # Handle additional vcard properties if present
        for old_key, new_key in {
            "hasTelephone": "vcard:hasTelephone",
            "hasURL": "vcard:hasURL",
            "organization-name": "vcard:organization-name",
            "street-address": "vcard:street-address",
            "locality": "vcard:locality",
            "region": "vcard:region",
            "postal-code": "vcard:postal-code",
            "country-name": "vcard:country-name"
        }.items():
            if old_key in contact_point:
                transformed[new_key] = contact_point[old_key]
        
        return transformed
    
    def transform_publisher(self, publisher: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform publisher from DCAT-US 1.1 format to DCAT-US 3.0 foaf:Organization format.
        
        In 1.1: {"name": "Agency Name", "subOrganizationOf": {"name": "Parent Org"}}
        In 3.0: {"@type": "org:Organization", "foaf:name": "Agency Name", "skos:prefLabel": "Agency Name", "org:subOrganizationOf": {...}}
        """
        transformed = {"@type": "org:Organization"}
        
        if "name" in publisher:
            transformed["foaf:name"] = publisher["name"]
            # SHACL requires skos:prefLabel for organizations
            transformed["skos:prefLabel"] = publisher["name"]
        
        # Handle sub-organization relationship
        if "subOrganizationOf" in publisher:
            sub_org = publisher["subOrganizationOf"]
            transformed_sub_org = {"@type": "org:Organization"}
            if "name" in sub_org:
                transformed_sub_org["foaf:name"] = sub_org["name"]
                transformed_sub_org["skos:prefLabel"] = sub_org["name"]
            transformed["org:subOrganizationOf"] = transformed_sub_org
        
        # Handle additional organization properties
        for old_key, new_key in {
            "mbox": "foaf:mbox",
            "homepage": "foaf:homepage",
            "identifier": "dcterms:identifier"
        }.items():
            if old_key in publisher:
                transformed[new_key] = publisher[old_key]
        
        return transformed
    
    def transform_distribution(self, distribution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform distribution from DCAT-US 1.1 to DCAT-US 3.0 format.
        Adds @type and proper prefixes to properties.
        """
        transformed = {"@type": "dcat:Distribution"}
        
        # Add required license if not present
        if "license" not in distribution:
            transformed["dcterms:license"] = {"@id": "https://creativecommons.org/publicdomain/zero/1.0/"}
        
        for old_key, value in distribution.items():
            if old_key in self.distribution_mapping:
                new_key = self.distribution_mapping[old_key]
                
                # Special handling for URLs - they should be IRIs, not literals
                if old_key in ["accessURL", "downloadURL"] and isinstance(value, str):
                    transformed[new_key] = {"@id": value}
                elif old_key == "describedBy" and isinstance(value, str):
                    transformed[new_key] = {"@id": value}
                else:
                    transformed[new_key] = value
            elif old_key not in ["@type", "@id"]:
                # For unmapped properties, print a warning
                print(f"Warning: Unmapped distribution property '{old_key}'")
        
        return transformed
    
    def transform_dataset(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single dataset from DCAT-US 1.1 to 3.0 format."""
        transformed = {"@type": "dcat:Dataset"}
        
        # Generate @id for dataset if identifier exists
        if "identifier" in dataset:
            # Create a proper IRI from the identifier
            base_id = dataset.get("@id", "https://data.gov/datasets/")
            if not base_id.endswith("/"):
                base_id += "/"
            transformed["@id"] = f"{base_id}{dataset['identifier']}"
        
        for old_key, value in dataset.items():
            if old_key in self.dataset_mapping:
                new_key = self.dataset_mapping[old_key]
                
                # Handle complex transformations
                if old_key == "contactPoint":
                    transformed[new_key] = self.transform_contact_point(value)
                elif old_key == "publisher":
                    transformed[new_key] = self.transform_publisher(value)
                elif old_key == "distribution" and isinstance(value, list):
                    transformed[new_key] = [self.transform_distribution(dist) for dist in value]
                elif old_key == "describedBy" and isinstance(value, str):
                    # In 3.0, describedBy should be an object with @id
                    transformed[new_key] = {"@id": value}
                elif old_key == "spatial" and isinstance(value, str):
                    # In 3.0, spatial should be a resource, not a literal
                    transformed[new_key] = {"@type": "dcterms:Location", "rdfs:label": value}
                elif old_key in ["modified", "issued"] and isinstance(value, str):
                    # Handle date formatting - convert ISO dates to proper XSD format
                    if value.startswith("R/"):
                        # This is a duration/frequency, which should be accrualPeriodicity instead
                        if new_key == "dcterms:modified":
                            # For modified dates that are durations, we'll skip and add a warning
                            print(f"Warning: Modified date '{value}' is a duration, not a date. Skipping.")
                            continue
                    else:
                        # Try to parse and format the date properly
                        import re
                        if re.match(r'\d{4}-\d{2}-\d{2}', value):
                            transformed[new_key] = {"@type": "xsd:date", "@value": value}
                        else:
                            transformed[new_key] = value
                elif old_key == "conformsTo" and isinstance(value, str):
                    # conformsTo should be an IRI
                    transformed[new_key] = {"@id": value}
                else:
                    # Direct mapping
                    transformed[new_key] = value
            elif old_key not in ["@type", "@id"]:
                # For unmapped properties, we'll print a warning but not include invalid JSON
                print(f"Warning: Unmapped property '{old_key}' in dataset")
        
        return transformed
    
    def convert_catalog(self, catalog_11: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a complete DCAT-US 1.1 catalog to DCAT-US 3.0 format."""
        
        # Start with the new context
        converted = {"@context": self.dcat_us_3_context}
        
        # Preserve @type and @id
        if "@type" in catalog_11:
            converted["@type"] = catalog_11["@type"]
        if "@id" in catalog_11:
            converted["@id"] = catalog_11["@id"]
        
        # Add default title and description if not present (often required by SHACL)
        if "title" not in catalog_11 and "dcterms:title" not in catalog_11:
            converted["dcterms:title"] = "Data Catalog"
        if "description" not in catalog_11 and "dcterms:description" not in catalog_11:
            converted["dcterms:description"] = "Government data catalog"
        
        # Add default publisher if not present (required by SHACL)
        if "publisher" not in catalog_11:
            converted["dcterms:publisher"] = {
                "@type": "org:Organization",
                "@id": "https://www.usa.gov/",
                "foaf:name": "U.S. Government",
                "skos:prefLabel": "U.S. Government"
            }
        
        # Transform catalog-level properties
        for old_key, value in catalog_11.items():
            if old_key in ["@context", "@type", "@id"]:
                continue  # Already handled
            
            if old_key in self.catalog_mapping:
                new_key = self.catalog_mapping[old_key]
                
                # Handle complex transformations
                if old_key == "dataset" and isinstance(value, list):
                    converted[new_key] = [self.transform_dataset(ds) for ds in value]
                elif old_key == "publisher":
                    converted[new_key] = self.transform_publisher(value)
                elif old_key == "contactPoint":
                    converted[new_key] = self.transform_contact_point(value)
                elif old_key == "describedBy" and isinstance(value, str):
                    # In 3.0, describedBy should be an object with @id
                    converted[new_key] = {"@id": value}
                elif old_key == "conformsTo" and isinstance(value, str):
                    # conformsTo should be an IRI
                    converted[new_key] = {"@id": value}
                else:
                    # Direct mapping
                    converted[new_key] = value
            elif old_key not in ["@context", "@type", "@id"]:
                # For unmapped properties, print a warning
                print(f"Warning: Unmapped catalog property '{old_key}'")
        
        return converted
    
    def convert_file(self, input_path: str, output_path: str) -> bool:
        """
        Convert a DCAT-US 1.1 JSON file to DCAT-US 3.0 JSON-LD format.
        
        Args:
            input_path: Path to the input DCAT-US 1.1 JSON file
            output_path: Path where the converted DCAT-US 3.0 file should be saved
            
        Returns:
            bool: True if conversion was successful, False otherwise
        """
        try:
            # Read the input file
            with open(input_path, 'r', encoding='utf-8') as f:
                catalog_11 = json.load(f)
            
            # Convert to DCAT-US 3.0
            catalog_30 = self.convert_catalog(catalog_11)
            
            # Write the output file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(catalog_30, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully converted {input_path} to {output_path}")
            return True
            
        except Exception as e:
            print(f"Error converting {input_path}: {str(e)}")
            return False


def main():
    """Main function to handle command line arguments and run the conversion."""
    parser = argparse.ArgumentParser(
        description="Convert DCAT-US 1.1 JSON files to DCAT-US 3.0 JSON-LD format"
    )
    parser.add_argument(
        "input", 
        help="Input DCAT-US 1.1 JSON file or directory containing JSON files"
    )
    parser.add_argument(
        "-o", "--output", 
        help="Output file or directory (defaults to input location with -v3.jsonld suffix)"
    )
    parser.add_argument(
        "--batch", 
        action="store_true",
        help="Process all JSON files in the input directory"
    )
    
    args = parser.parse_args()
    
    converter = DCATUSConverter()
    
    if args.batch or os.path.isdir(args.input):
        # Batch processing
        input_dir = args.input
        output_dir = args.output or input_dir
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        success_count = 0
        total_count = 0
        
        for filename in os.listdir(input_dir):
            if filename.endswith('.json'):
                input_path = os.path.join(input_dir, filename)
                output_filename = filename.replace('.json', '-v3.jsonld')
                output_path = os.path.join(output_dir, output_filename)
                
                total_count += 1
                if converter.convert_file(input_path, output_path):
                    success_count += 1
        
        print(f"\nBatch conversion completed: {success_count}/{total_count} files converted successfully")
    
    else:
        # Single file processing
        input_path = args.input
        
        if args.output:
            output_path = args.output
        else:
            # Generate default output filename
            base_name = os.path.splitext(input_path)[0]
            output_path = f"{base_name}-v3.jsonld"
        
        success = converter.convert_file(input_path, output_path)
        if not success:
            exit(1)


if __name__ == "__main__":
    main()