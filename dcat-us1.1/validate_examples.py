#!/usr/bin/env python3
"""
DCAT-US 1.1 JSON Schema Validator

This script validates JSON examples against the DCAT-US 1.1 schema files.

Usage:
    python validate_examples.py                 # Validate all files in examples/ directory
    python validate_examples.py <json_file>     # Validate a specific JSON file
"""

import json
import os
import sys
import warnings
from pathlib import Path
from jsonschema import validate, ValidationError

# Suppress deprecation warnings for cleaner output
warnings.filterwarnings("ignore", message=".*RefResolver.*", category=DeprecationWarning)

def load_json_file(filepath):
    """Load and parse a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to load {filepath}: {e}")
        return None

def validate_example(example_file, schema, schema_store):
    """Validate a single JSON example file against the schema."""
    example_data = load_json_file(example_file)
    if example_data is None:
        return False
    
    try:
        # Use the validate function with schema store for resolving references
        import jsonschema
        resolver = jsonschema.RefResolver.from_schema(schema, store=schema_store)
        validate(instance=example_data, schema=schema, resolver=resolver)
        print(f"SUCCESS: {example_file.name} conforms to DCAT-US 1.1 JSON Schema")
        return True
    except ValidationError as e:
        print(f"FAILURE: {example_file.name} does not conform to DCAT-US 1.1 JSON Schema")
        print(f"  Error: {e.message}")
        if e.absolute_path:
            print(f"  Path: {' -> '.join(str(p) for p in e.absolute_path)}")
        return False

def main():
    """Main validation function."""
    # Check for help argument
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0)

    print("=== DCAT-US 1.1 JSON Schema Validation ===")
    print()
    
    # Set up paths
    script_dir = Path(__file__).parent
    examples_dir = script_dir / "examples"
    catalog_schema_path = script_dir / "catalog.json"
    dataset_schema_path = script_dir / "dataset.json"
    
    # Load schemas
    print("Loading schemas...")
    catalog_schema = load_json_file(catalog_schema_path)
    dataset_schema = load_json_file(dataset_schema_path)
    
    if catalog_schema is None or dataset_schema is None:
        print("ERROR: Failed to load required schemas")
        sys.exit(1)
    
    # Create a resolver for schema references
    schema_store = {
        str(catalog_schema_path): catalog_schema,
        str(dataset_schema_path): dataset_schema,
        "dataset.json": dataset_schema  # For relative references
    }
    
    # Check for command-line arguments for single file validation
    if len(sys.argv) == 2:
        # Single file validation mode
        json_file = Path(sys.argv[1])

        if not json_file.exists():
            print(f"ERROR: File {json_file} not found")
            sys.exit(1)
        
        print(f"\n=== VALIDATION RESULTS FOR {json_file} ===")
        success = validate_example(json_file, catalog_schema, schema_store)
        sys.exit(0 if success else 1)
    elif len(sys.argv) > 2:
        print("ERROR: Too many arguments provided")
        print(__doc__)
        sys.exit(1)
    
    # Find all JSON example files
    if not examples_dir.exists():
        print(f"ERROR: Examples directory not found: {examples_dir}")
        sys.exit(1)
    
    json_files = list(examples_dir.glob("*.json"))
    if not json_files:
        print(f"WARNING: No JSON files found in {examples_dir}")
        sys.exit(0)
    
    print(f"Found {len(json_files)} JSON example files")
    print("=" * 60)
    
    # Validate each example
    success_count = 0
    failure_count = 0
    
    for example_file in sorted(json_files):
        if validate_example(example_file, catalog_schema, schema_store):
            success_count += 1
        else:
            failure_count += 1
        print()  # Add spacing between results
    
    # Summary
    print("=" * 60)
    print("JSON SCHEMA VALIDATION SUMMARY:")
    print(f"  Total files processed: {len(json_files)}")
    print(f"  Successful validations: {success_count}")
    print(f"  Failed validations: {failure_count}")
    
    if failure_count > 0:
        sys.exit(1)
    else:
        print("All validations passed successfully")

if __name__ == "__main__":
    main()