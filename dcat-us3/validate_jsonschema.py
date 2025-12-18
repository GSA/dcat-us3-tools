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
from jsonschema import Draft7Validator, ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

# Base URL for the DCAT-US 3.0 JSON Schema files
SCHEMA_BASE_URL = "https://raw.githubusercontent.com/GSA/dcat-us3-tools/refs/heads/main/dcat-us3/jsonschema/"
SCHEMA_ROOT_URL = SCHEMA_BASE_URL + "dcat_us_3.0.0_schema.json"

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


def retrieve_from_url(uri: str):
    """Retrieve a schema resource from a URL for the referencing library."""
    schema = fetch_schema(uri)
    return Resource.from_contents(schema, default_specification=DRAFT7)


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


def build_registry_with_remote_schemas() -> tuple[dict, Registry]:
    """
    Fetch the root schema and all referenced definition schemas from GitHub.
    
    Returns a tuple of (root_schema, registry) where the registry contains
    all the definition schemas needed for $ref resolution.
    """
    print(f"  Fetching root schema from {SCHEMA_ROOT_URL}")
    root_schema = fetch_schema(SCHEMA_ROOT_URL)
    
    # Build a list of all definition URLs we need to fetch
    definitions = root_schema.get("definitions", {})
    resources = []
    
    for def_name, def_value in definitions.items():
        if "$ref" in def_value:
            ref_path = def_value["$ref"]
            # Convert relative path to absolute URL
            def_url = urljoin(SCHEMA_BASE_URL, ref_path)
            print(f"  Fetching {def_name} from {def_url}")
            
            try:
                def_schema = fetch_schema(def_url)
                # Remove $id properties that break reference resolution
                def_schema = remove_schema_ids(def_schema)
                resource = Resource.from_contents(def_schema, default_specification=DRAFT7)
                resources.append((def_url, resource))
            except Exception as e:
                print(f"  WARNING: Failed to fetch {def_name}: {e}")
    
    # Create registry with all fetched schemas
    registry = Registry().with_resources(resources)
    
    # Now rewrite the root schema to use absolute URLs for $ref
    rewritten_definitions = {}
    for def_name, def_value in definitions.items():
        if "$ref" in def_value:
            ref_path = def_value["$ref"]
            def_url = urljoin(SCHEMA_BASE_URL, ref_path)
            rewritten_definitions[def_name] = {"$ref": def_url}
        else:
            rewritten_definitions[def_name] = def_value
    
    root_schema["definitions"] = rewritten_definitions
    
    return root_schema, registry

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

def validate_example(example_file, main_schema, registry, expect_valid=True):
    """Validate a single JSON-LD example file against the schema.
    
    Args:
        example_file: Path to the JSON-LD file
        main_schema: The JSON schema to validate against
        registry: The referencing Registry for resolving $ref references
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
        # Create validator with registry for $ref resolution
        validator = Draft7Validator(main_schema, registry=registry)
        
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
        main_schema, registry = build_registry_with_remote_schemas()
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
        success = validate_example(jsonld_file, main_schema, registry)
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
            if validate_example(example_file, main_schema, registry, expect_valid=True):
                pass_count += 1
            else:
                fail_count += 1
    
    # Validate "bad" examples (expected to be invalid)
    if bad_files:
        print("\n--- Validating 'bad' examples (expected to be INVALID) ---\n")
        for example_file in sorted(bad_files):
            if validate_example(example_file, main_schema, registry, expect_valid=False):
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