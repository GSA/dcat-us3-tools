#!/usr/bin/env python3
"""
DCAT-US 3.0 JSON Schema Validator

This script validates JSON-LD examples against the DCAT-US 3.0 JSON Schema file.

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
import jsonschema_rs

# Local path to the DCAT-US 3.0 JSON Schema file
SCHEMA_FILENAME = "dcat-us3.0-expanded-schema.json"


def load_schema(schema_path: Path) -> dict:
    """
    Load the DCAT-US 3.0 JSON Schema from the local file.
    
    Args:
        schema_path: Path to the JSON schema file
    
    Returns:
        The loaded schema as a dictionary
    """
    return load_json_file(schema_path)


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

def collect_all_validation_errors(validator, data):
    """Collect all validation errors from jsonschema-rs validator."""
    errors = []
    
    try:
        # jsonschema-rs validate() raises ValidationError on first error
        # Use iter_errors() to get all errors
        for error in validator.iter_errors(data):
            errors.append(error)
    except Exception as e:
        # Fallback for any unexpected errors
        errors.append(str(e))
    
    return errors


def get_field_path_from_error(error) -> str:
    """Extract a readable field path from jsonschema-rs validation error."""
    # jsonschema-rs errors have an instance_path attribute
    if hasattr(error, 'instance_path'):
        path = error.instance_path
        if path:
            # instance_path is a list of path components, convert to string
            if isinstance(path, list):
                if len(path) == 0:
                    return "$"
                # Convert list to JSON pointer notation (e.g., /field/nested)
                return "/" + "/".join(str(component) for component in path)
            return str(path)
    return "$"


def get_error_message(error) -> str:
    """Extract the error message from a jsonschema-rs validation error."""
    if hasattr(error, 'message'):
        return error.message
    return str(error)

def group_errors_by_field(errors):
    """Group validation errors by field path for better reporting."""
    grouped = defaultdict(list)
    
    for error in errors:
        field_path = get_field_path_from_error(error)
        message = get_error_message(error)
        grouped[field_path].append(message)
    
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

def validate_example(example_file, main_schema, expect_valid=True):
    """Validate a single JSON-LD example file against the schema.
    
    Args:
        example_file: Path to the JSON-LD file
        main_schema: The JSON schema to validate against
        expect_valid: If True, file should pass validation. If False, file should fail.
    
    Returns:
        True if result matches expectation, False otherwise
    """
    try:
        example_data = load_json_file(example_file)
    except Exception as e:
        print(f"ERROR: Failed to load {example_file}: {e}")
        return False
    
    if example_data is None:
        return False
    
    try:
        # Create jsonschema-rs validator
        validator = jsonschema_rs.validator_for(main_schema)
        
        # Collect all validation errors
        all_errors = collect_all_validation_errors(validator, example_data)
        
        is_valid = len(all_errors) == 0
        result_matches_expectation = is_valid == expect_valid
        
        if is_valid:
            if expect_valid:
                print(f"✅ PASS: {example_file.name} is valid (as expected)")
            else:
                print(f"❌ UNEXPECTED: {example_file.name} is valid but expected to be INVALID")
            return result_matches_expectation
        
        # File has validation errors
        if expect_valid:
            # Expected valid but got errors - this is a failure
            print(f"❌ UNEXPECTED: {example_file.name} is invalid but expected to be VALID")
            print(f"   Found {len(all_errors)} validation issue(s):")
        else:
            # Expected invalid and got errors - this is correct
            print(f"✅ PASS: {example_file.name} is invalid (as expected)")
            print(f"   Found {len(all_errors)} validation issue(s):")
        
        # Group and format errors
        grouped_errors = group_errors_by_field(all_errors)
        formatted_errors = format_validation_errors(grouped_errors)
        
        print()
        for i, error_msg in enumerate(formatted_errors, 1):
            print(f"   {i:2d}. {error_msg}")
        
        print()
        return result_matches_expectation
        
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
    schema_path = script_dir / "jsonschema" / SCHEMA_FILENAME
    
    # Load schema from local file
    print(f"Loading schema from {schema_path.relative_to(script_dir.parent)}...")
    if not schema_path.exists():
        print(f"ERROR: Schema file not found at {schema_path}")
        sys.exit(1)
    
    try:
        main_schema = load_schema(schema_path)
        if main_schema is None:
            raise RuntimeError("Failed to parse schema file")
    except Exception as e:
        print(f"ERROR: Failed to load schema: {e}")
        sys.exit(1)
    
    print("Schema loaded successfully.\n")
    
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
    
    # Find all JSON-LD example files in good/ and bad/ subdirectories
    good_dir = examples_dir / "good"
    bad_dir = examples_dir / "bad"
    
    if not good_dir.exists() and not bad_dir.exists():
        print(f"ERROR: Neither 'good' nor 'bad' subdirectory found in {examples_dir}")
        sys.exit(1)
    
    good_files = []
    bad_files = []
    
    if good_dir.exists():
        good_files = list(good_dir.glob("*.jsonld")) + list(good_dir.glob("*.json"))
    
    if bad_dir.exists():
        bad_files = list(bad_dir.glob("*.jsonld")) + list(bad_dir.glob("*.json"))
    
    total_files = len(good_files) + len(bad_files)
    if total_files == 0:
        print(f"WARNING: No JSON-LD files found in {examples_dir}/good or {examples_dir}/bad")
        sys.exit(0)
    
    print(f"Found {len(good_files)} 'good' (expected valid) and {len(bad_files)} 'bad' (expected invalid) example files")
    print("=" * 60)
    
    # Validate each example
    pass_count = 0
    fail_count = 0
    
    # Validate "good" examples (expected to be valid)
    if good_files:
        print("\n--- Validating 'good' examples (expected to be VALID) ---\n")
        for example_file in sorted(good_files):
            if validate_example(example_file, main_schema, expect_valid=True):
                pass_count += 1
            else:
                fail_count += 1
    
    # Validate "bad" examples (expected to be invalid)
    if bad_files:
        print("\n--- Validating 'bad' examples (expected to be INVALID) ---\n")
        for example_file in sorted(bad_files):
            if validate_example(example_file, main_schema, expect_valid=False):
                pass_count += 1
            else:
                fail_count += 1
    
    # Summary
    print("=" * 60)
    print("JSON SCHEMA VALIDATION SUMMARY:")
    print(f"  Total files processed: {total_files}")
    print(f"  Results matching expectations: {pass_count}")
    print(f"  Results NOT matching expectations: {fail_count}")
    
    if fail_count > 0:
        sys.exit(1)
    else:
        print("\nAll validations matched expectations!")

if __name__ == "__main__":
    main()