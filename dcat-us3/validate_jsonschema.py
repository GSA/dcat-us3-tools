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

# Suppress deprecation warnings for cleaner output since we're handling references manually
warnings.filterwarnings("ignore", category=DeprecationWarning, module="jsonschema")

def resolve_schema_refs(schema, schema_store, resolved_cache=None):
    """Recursively resolve all $ref references in a schema."""
    if resolved_cache is None:
        resolved_cache = set()
    
    if isinstance(schema, dict):
        if "$ref" in schema:
            ref_path = schema["$ref"]
            
            # Avoid infinite recursion for circular references
            cache_key = ref_path
            if cache_key in resolved_cache:
                # For circular references, return a simplified schema
                return {"type": "object", "additionalProperties": True}
            
            resolved_cache.add(cache_key)
            
            # Try to resolve the reference
            if ref_path in schema_store:
                resolved_schema = resolve_schema_refs(schema_store[ref_path], schema_store, resolved_cache)
                resolved_cache.discard(cache_key)
                return resolved_schema
            elif ref_path.startswith("#/definitions/"):
                # Handle internal definitions
                def_name = ref_path.split("/")[-1]
                if "definitions" in schema and def_name in schema["definitions"]:
                    resolved_schema = resolve_schema_refs(schema["definitions"][def_name], schema_store, resolved_cache)
                    resolved_cache.discard(cache_key)
                    return resolved_schema
            
            resolved_cache.discard(cache_key)
            # If we can't resolve, return a permissive schema
            return {"type": "object", "additionalProperties": True}
        else:
            # Recursively process all properties
            result = {}
            for key, value in schema.items():
                result[key] = resolve_schema_refs(value, schema_store, resolved_cache)
            return result
    elif isinstance(schema, list):
        return [resolve_schema_refs(item, schema_store, resolved_cache) for item in schema]
    else:
        return schema

def create_inline_schema(main_schema, schema_store):
    """Create a self-contained schema with all references resolved."""
    # Get the Catalog schema and resolve all its references
    catalog_ref = main_schema["definitions"]["Catalog"]["$ref"]
    
    if catalog_ref in schema_store:
        catalog_schema = schema_store[catalog_ref]
        
        # Create a complete definitions dictionary with resolved schemas
        resolved_definitions = {}
        for def_name, def_schema in main_schema.get("definitions", {}).items():
            resolved_definitions[def_name] = resolve_schema_refs(def_schema, schema_store)
        
        # Resolve the catalog schema with all definitions available
        resolved_catalog = resolve_schema_refs(catalog_schema, schema_store)
        
        # Create the final schema
        complete_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            **resolved_catalog,
            "definitions": resolved_definitions
        }
        
        return complete_schema
    else:
        # Fallback approach
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
            "additionalProperties": True,
            "definitions": main_schema.get("definitions", {})
        }

def load_json_file(filepath):
    """Load and parse a JSON or JSON-LD file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to load {filepath}: {e}")
        return None

def load_schema_store(schema_dir):
    """Load all schema definition files into a store for reference resolution."""
    schema_store = {}
    definitions_dir = schema_dir / "definitions"
    
    if definitions_dir.exists():
        for schema_file in definitions_dir.glob("*.json"):
            schema_data = load_json_file(schema_file)
            if schema_data:
                # Store with relative path for reference resolution
                relative_path = f"definitions/{schema_file.name}"
                schema_store[relative_path] = schema_data
                # Also store with absolute path
                schema_store[str(schema_file)] = schema_data
    
    return schema_store

def validate_example(example_file, main_schema, schema_store):
    """Validate a single JSON-LD example file against the schema."""
    try:
      example_data = load_json_file(example_file)
    except Exception as e:
      print(f"ERROR: Failed to load {example_file}: {e}")
      return False
    
    if example_data is None:
        return False
    
    try:
        # Create a self-contained schema with all definitions inlined
        complete_schema = create_inline_schema(main_schema, schema_store)
        
        # Create a simple validator without custom resolvers
        validator = Draft7Validator(complete_schema)
        
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
    main_schema_path = schema_dir / "dcat_us_3.0.0_schema.json"
    
    # Load main schema
    print("Loading schemas...")
    main_schema = load_json_file(main_schema_path)
    
    if main_schema is None:
        print("ERROR: Failed to load main schema")
        sys.exit(1)
    
    # Load all schema definitions into a store
    schema_store = load_schema_store(schema_dir)
    schema_store[str(main_schema_path)] = main_schema
    
    print(f"Loaded main schema and {len(schema_store)-1} definition schemas")
    
    # Check for command-line arguments for single file validation
    if len(sys.argv) == 2:
        # Single file validation mode
        jsonld_file = Path(sys.argv[1])

        if not jsonld_file.exists():
            print(f"ERROR: File {jsonld_file} not found")
            sys.exit(1)
        
        print(f"\n=== VALIDATION RESULTS FOR {jsonld_file} ===")
        success = validate_example(jsonld_file, main_schema, schema_store)
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
        if validate_example(example_file, main_schema, schema_store):
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