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
from urllib.parse import urljoin
import requests
import jsonschema_rs

# Base URL for the DCAT-US 3.0 JSON Schema files
SCHEMA_BASE_URL = "https://raw.githubusercontent.com/GSA/dcat-us3-tools/refs/heads/main/dcat-us3/jsonschema/"
SCHEMA_ROOT_URL = SCHEMA_BASE_URL + "/definitions/Catalog.json"

# Cache for fetched schemas
_schema_cache = {}


def fetch_schema(url: str) -> dict:
    """Fetch a JSON schema from a URL with caching."""
    if url in _schema_cache:
        return _schema_cache[url]
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        schema = response.json()
        _schema_cache[url] = schema
        return schema
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch schema from {url}: {e}")


def resolve_refs_recursively(obj, base_url: str, visited: set = None) -> dict:
    """
    Recursively resolve all $ref references in a schema by fetching and inlining them.
    
    This is necessary because jsonschema-rs may have trouble fetching remote URLs
    during validation. By resolving all refs upfront using Python's requests library,
    we ensure the schema is self-contained.
    
    Args:
        obj: The schema object to process
        base_url: The base URL for resolving relative references
        visited: Set of already-visited URLs to prevent infinite recursion
    
    Returns:
        The schema with all $ref references resolved and inlined
    """
    if visited is None:
        visited = set()
    
    if isinstance(obj, dict):
        # Check if this is a $ref that points to a URL
        if "$ref" in obj and isinstance(obj["$ref"], str):
            ref = obj["$ref"]
            
            # Only resolve HTTP(S) URLs, not local #/definitions/ refs
            if ref.startswith("http://") or ref.startswith("https://"):
                if ref in visited:
                    # Already resolved this, return a reference to avoid infinite loop
                    return obj
                
                visited.add(ref)
                
                try:
                    # Fetch the referenced schema
                    referenced_schema = fetch_schema(ref)
                    # Remove $id to prevent base URI changes
                    referenced_schema = remove_schema_ids(referenced_schema)
                    # Recursively resolve any refs in the fetched schema
                    resolved = resolve_refs_recursively(referenced_schema, ref, visited)
                    
                    # Merge any additional properties from the original $ref object
                    # (like "description") into the resolved schema
                    other_props = {k: v for k, v in obj.items() if k != "$ref"}
                    if other_props and isinstance(resolved, dict):
                        resolved = {**resolved, **other_props}
                    
                    return resolved
                except Exception as e:
                    print(f"  WARNING: Failed to resolve $ref {ref}: {e}")
                    return obj
        
        # Recursively process all values in the dict
        return {key: resolve_refs_recursively(value, base_url, visited) for key, value in obj.items()}
    
    elif isinstance(obj, list):
        return [resolve_refs_recursively(item, base_url, visited) for item in obj]
    
    else:
        return obj


def load_json_file(filepath):
    """Load and parse a JSON or JSON-LD file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to load {filepath}: {e}")
        return None


def remove_schema_ids(obj):
    """
    Recursively remove $id properties from a schema object.
    
    The $id property changes the base URI for JSON Pointer resolution,
    which breaks #/definitions/... references in newer jsonschema versions.
    Removing them allows references to resolve from the root schema.
    
    Note: This only removes $id from nested objects, not the root $schema.
    """
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if key == "$id":
                continue  # Skip $id properties
            result[key] = remove_schema_ids(value)
        return result
    elif isinstance(obj, list):
        return [remove_schema_ids(item) for item in obj]
    else:
        return obj


def build_registry_with_remote_schemas() -> dict:
    """
    Fetch the root schema and all referenced definition schemas from GitHub.
    
    Returns the root schema with all definitions inlined for jsonschema-rs.
    This recursively resolves ALL $ref references to remote URLs, ensuring
    the schema is completely self-contained and jsonschema-rs doesn't need
    to make any HTTP calls during validation.
    """
    print(f"  Fetching root schema from {SCHEMA_ROOT_URL}")
    root_schema = fetch_schema(SCHEMA_ROOT_URL)
    
    # Recursively resolve all $ref references in the entire schema
    print("  Resolving all remote $ref references...")
    resolved_schema = resolve_refs_recursively(root_schema, SCHEMA_ROOT_URL)
    
    # Remove any remaining $id properties that could break reference resolution
    resolved_schema = remove_schema_ids(resolved_schema)
    
    return resolved_schema

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
            return path
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
    
    # Load schemas from GitHub
    print("Loading schemas from GitHub...")
    try:
        main_schema = build_registry_with_remote_schemas()
    except Exception as e:
        print(f"ERROR: Failed to load schemas: {e}")
        sys.exit(1)
    
    print("Schemas loaded successfully.\n")
    
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