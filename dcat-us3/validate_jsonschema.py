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
import re
from pathlib import Path
from collections import defaultdict
from jsonschema import Draft7Validator, ValidationError

def load_json_file(filepath):
    """Load and parse a JSON or JSON-LD file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to load {filepath}: {e}")
        return None

def get_format_from_message(validation_msg: str) -> str:
    """Extract the format/rule from validation error message."""
    if "too long" in validation_msg:
        return "max string length requirement"
    if "was expected" in validation_msg:
        return f"constant value {validation_msg}"
    if "is not valid under any of the given schemas" in validation_msg:
        return "schema mismatch"
    if "is not of type" in validation_msg:
        return validation_msg
    if "does not match" in validation_msg:
        return "format requirement"
    if "is a required property" in validation_msg:
        return "required field"
    return validation_msg.split(" ")[-1] if validation_msg else "unknown"

def get_field_path(error: ValidationError) -> str:
    """Extract a readable field path from validation error."""
    if error.absolute_path:
        path_parts = []
        for part in error.absolute_path:
            if isinstance(part, int):
                path_parts.append(f"[{part}]")
            else:
                path_parts.append(str(part))
        return ".".join(path_parts).replace(".[", "[")
    return "$"

def found_simple_message(validation_error: ValidationError) -> bool:
    """Determine if this is a root-level simple error."""
    field_path = get_field_path(validation_error)
    
    # Root level errors are simple
    if field_path == "$":
        return True
    
    # Dict/object and list/array errors at deeper levels may need recursion
    if isinstance(validation_error.instance, (dict, list)):
        # Empty containers are simple errors
        if not validation_error.instance:
            return True
        # Non-empty containers with context need recursion
        if validation_error.context:
            return False
    
    # Primitive value errors are simple
    return True

def collect_all_validation_errors(validator, data):
    """Collect all validation errors recursively."""
    errors = []
    
    def collect_errors(error):
        if found_simple_message(error):
            errors.append(error)
        else:
            # Recurse through context errors
            for context_error in error.context:
                collect_errors(context_error)
    
    # Get all errors from validator
    for error in validator.iter_errors(data):
        collect_errors(error)
    
    return errors

def group_errors_by_field(errors):
    """Group validation errors by field path for better reporting."""
    grouped = defaultdict(list)
    
    for error in errors:
        field_path = get_field_path(error)
        grouped[field_path].append(error.message)
    
    return grouped

def format_validation_errors(grouped_errors):
    """Format grouped errors into human-readable messages."""
    formatted_errors = []
    
    for field_path, messages in grouped_errors.items():
        if field_path == "$":
            # Root level errors
            for message in messages:
                formatted_errors.append(f"Root level: {message}")
        else:
            # Field-specific errors - extract the main issue
            if len(messages) == 1:
                message = messages[0]
                # Extract the core issue from verbose error messages
                if "is not of type" in message:
                    # Extract what type it should be
                    type_match = re.search(r"is not of type '([^']+)'", message)
                    if type_match:
                        expected_type = type_match.group(1)
                        formatted_errors.append(f"Field '{field_path}': Expected {expected_type}, but got a different type")
                    else:
                        formatted_errors.append(f"Field '{field_path}': Type mismatch")
                elif "is a required property" in message:
                    prop_name = message.split("'")[1] if "'" in message else "property"
                    formatted_errors.append(f"Field '{field_path}': Missing required property '{prop_name}'")
                elif "does not match" in message:
                    formatted_errors.append(f"Field '{field_path}': Format validation failed")
                elif "too long" in message:
                    formatted_errors.append(f"Field '{field_path}': Value exceeds maximum length")
                else:
                    # Truncate very long messages for readability
                    if len(message) > 200:
                        message = message[:200] + "..."
                    formatted_errors.append(f"Field '{field_path}': {message}")
            else:
                # Multiple issues with same field
                type_errors = [msg for msg in messages if "is not of type" in msg]
                if type_errors and len(type_errors) == len(messages):
                    # All are type errors, summarize
                    types = []
                    for msg in type_errors:
                        type_match = re.search(r"is not of type '([^']+)'", msg)
                        if type_match:
                            types.append(type_match.group(1))
                    if types:
                        formatted_errors.append(f"Field '{field_path}': Expected one of [{', '.join(set(types))}], but got a different type")
                    else:
                        formatted_errors.append(f"Field '{field_path}': Multiple type validation failures")
                else:
                    formatted_errors.append(f"Field '{field_path}': {len(messages)} validation issues")
    
    return formatted_errors

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
        # Create validator
        validator = Draft7Validator(main_schema)
        
        # Collect all validation errors
        all_errors = collect_all_validation_errors(validator, example_data)
        
        if not all_errors:
            print(f"✅ SUCCESS: {example_file.name} conforms to DCAT-US 3.0 JSON Schema")
            return True
        
        # Group and format errors
        grouped_errors = group_errors_by_field(all_errors)
        formatted_errors = format_validation_errors(grouped_errors)
        
        print(f"❌ FAILURE: {example_file.name} does not conform to DCAT-US 3.0 JSON Schema")
        print(f"   Found {len(all_errors)} validation issue(s) across {len(grouped_errors)} field(s):")
        print()
        
        for i, error_msg in enumerate(formatted_errors, 1):
            print(f"   {i:2d}. {error_msg}")
        
        print()
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