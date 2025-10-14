#!/usr/bin/env python3
"""
DCAT-US 3.0 JSON Schema Validator

This script validates JSON-LD examples against the DCAT-US 3.0 JSON Schema files.

Usage:
    python validate_jsonschema.py                       # Validate all files in examples/ directory
    python validate_jsonschema.py <jsonld_file>         # Validate a specific JSON-LD file
"""

import json
import os
import sys
import warnings
from pathlib import Path
from jsonschema import Draft7Validator, ValidationError

def load_json_file(filepath):
    """Load and parse a JSON or JSON-LD file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to load {filepath}: {e}")
        return None

def validate_example(example_file, main_schema):
    """Validate a single JSON-LD example file against the schema."""
    try:
      example_data = load_json_file(example_file)
    except Exception as e:
      print(f"ERROR: Failed to load {example_file}: {e}")
      return False
    
    if example_data is None:
        return False
    
    try:
        
        # Create a simple validator without custom resolvers
        validator = Draft7Validator(main_schema)
        
        # Validate against the complete schema
        validator.validate(example_data)
        print(f"SUCCESS: {example_file.name} conforms to DCAT-US 3.0 JSON Schema")
        return True
    except ValidationError as e:
        print(f"FAILURE: {example_file.name} does not conform to DCAT-US 3.0 JSON Schema")
        print(f"  Error: {e.message}")
        if e.absolute_path:
            print(f"  Path: {' -> '.join(str(p) for p in e.absolute_path)}")
        if e.schema_path:
            print(f"  Schema Path: {' -> '.join(str(p) for p in e.schema_path)}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to validate {example_file.name}: {e}")
        return False

def main():
    """Main validation function."""
    # Check for help argument
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0)

    print("=== DCAT-US 3.0 JSON Schema Validation ===")
    print()
    
    # Set up paths
    script_dir = Path(__file__).parent
    examples_dir = script_dir / "examples"
    schema_dir = script_dir / "jsonschema"
    main_schema_path = schema_dir / "dcat-us3.0-expanded-schema.json"
    
    # Load main schema
    print("Loading schemas...")
    main_schema = load_json_file(main_schema_path)
    
    if main_schema is None:
        print("ERROR: Failed to load main schema")
        sys.exit(1)
    
    # Check for command-line arguments for single file validation
    if len(sys.argv) == 2:
        # Single file validation mode
        jsonld_file = Path(sys.argv[1])

        if not jsonld_file.exists():
            print(f"ERROR: File {jsonld_file} not found")
            sys.exit(1)
        
        print(f"\n=== VALIDATION RESULTS FOR {jsonld_file} ===")
        success = validate_example(jsonld_file, main_schema)
        sys.exit(0 if success else 1)
    elif len(sys.argv) > 2:
        print("ERROR: Too many arguments provided")
        print(__doc__)
        sys.exit(1)
    
    # Find all JSON-LD example files
    if not examples_dir.exists():
        print(f"ERROR: Examples directory not found: {examples_dir}")
        sys.exit(1)
    
    jsonld_files = list(examples_dir.glob("*.jsonld")) + list(examples_dir.glob("*.json"))
    if not jsonld_files:
        print(f"WARNING: No JSON-LD files found in {examples_dir}")
        sys.exit(0)
    
    print(f"Found {len(jsonld_files)} JSON-LD example files")
    print("=" * 60)
    
    # Validate each example
    success_count = 0
    failure_count = 0
    
    for example_file in sorted(jsonld_files):
        if validate_example(example_file, main_schema):
            success_count += 1
        else:
            failure_count += 1
        print()  # Add spacing between results
    
    # Summary
    print("=" * 60)
    print("JSON SCHEMA VALIDATION SUMMARY:")
    print(f"  Total files processed: {len(jsonld_files)}")
    print(f"  Successful validations: {success_count}")
    print(f"  Failed validations: {failure_count}")
    
    if failure_count > 0:
        sys.exit(1)
    else:
        print("All validations passed successfully")

if __name__ == "__main__":
    main()