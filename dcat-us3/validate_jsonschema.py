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


def extract_required_property_name(message: str) -> str:
    """Extract the property name from a 'is a required property' error message.
    
    Handles both single and double quote formats from different JSON schema validators.
    """
    # Try double quotes first (jsonschema-rs format)
    match = re.search(r'"([^"]+)" is a required property', message)
    if match:
        return match.group(1)
    # Try single quotes
    match = re.search(r"'([^']+)' is a required property", message)
    if match:
        return match.group(1)
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


def create_dataset_schema(main_schema):
    """Create a standalone schema for validating individual Dataset objects.
    
    This extracts the Dataset definition and all its dependencies from the main schema
    so we can validate datasets directly and get more specific error messages.
    """
    dataset_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Dataset Validation Schema",
        "$ref": "#/$defs/Dataset",
        "$defs": main_schema.get("$defs", {})
    }
    return dataset_schema


def validate_dataset_directly(dataset_obj, dataset_index, dataset_schema):
    """Validate a single dataset object directly against the Dataset schema.
    
    Returns a list of formatted error messages with specific field information.
    """
    errors = []
    nested_oneOf_fields = {}  # Track fields with oneOf errors for deeper validation
    
    try:
        validator = jsonschema_rs.validator_for(dataset_schema)
        
        for error in validator.iter_errors(dataset_obj):
            instance_path = error.instance_path if hasattr(error, 'instance_path') else []
            message = error.message if hasattr(error, 'message') else str(error)
            
            # Build the field path
            if instance_path:
                if isinstance(instance_path, list):
                    field_path = ".".join(str(p) for p in instance_path)
                else:
                    field_path = str(instance_path)
            else:
                field_path = "(root)"
            
            # Check if this is a nested oneOf error that we can drill into
            if ("is not valid under any of the schemas listed in the 'oneOf'" in message and
                instance_path and len(instance_path) >= 1):
                field_name = instance_path[0] if isinstance(instance_path, list) else instance_path
                nested_oneOf_fields[field_name] = instance_path
            elif field_path == "(root)" and "is a required property" in message:
                # Root-level required property error - extract the property name and format nicely
                prop_name = extract_required_property_name(message)
                if prop_name:
                    errors.append(f"dataset[{dataset_index}]: Missing required field '{prop_name}'")
                else:
                    errors.append(f"dataset[{dataset_index}]: Missing required field")
            else:
                # Format the error message
                formatted_msg = format_single_error(field_path, message, dataset_index)
                errors.append(formatted_msg)
        
        # For nested oneOf errors, try to get more specific info
        for field_name, instance_path in nested_oneOf_fields.items():
            field_value = dataset_obj.get(field_name) if isinstance(dataset_obj, dict) else None
            
            if field_value is not None:
                detailed_errors = analyze_nested_oneOf_error(
                    field_name, field_value, dataset_index, dataset_schema
                )
                errors.extend(detailed_errors)
    
    except Exception as e:
        errors.append(f"dataset[{dataset_index}]: Error during validation - {e}")
    
    return errors


def analyze_nested_oneOf_error(field_name, field_value, dataset_index, main_schema):
    """Analyze a nested oneOf error and provide specific details about why it failed.
    
    For fields like publisher, distribution, contactPoint, etc., this digs into
    the actual schema requirements to explain what's wrong.
    """
    errors = []
    defs = main_schema.get("$defs", {})
    
    # Map field names to their expected object types
    field_type_mapping = {
        "publisher": "Organization",
        "contactPoint": "Kind",
        "distribution": "Distribution",
        "spatial": "Location",
        "temporal": "PeriodOfTime",
        "creator": "Organization",
        "contributor": "Organization",
        "rights": "RightsStatement",
        "license": "LicenseDocument",
    }
    
    expected_type = field_type_mapping.get(field_name)
    
    if expected_type and isinstance(field_value, dict):
        # It's an object, validate against the expected type definition
        type_def = defs.get(expected_type, {})
        required_fields = type_def.get("required", [])
        properties = type_def.get("properties", {})
        
        # Check for missing required fields
        missing_required = [f for f in required_fields if f not in field_value]
        if missing_required:
            for field in missing_required:
                errors.append(f"dataset[{dataset_index}].{field_name}: Missing required property '{field}' (required by {expected_type})")
        
        # Check for fields that might have wrong types
        for prop_name, prop_value in field_value.items():
            if prop_name.startswith("@"):
                continue  # Skip JSON-LD keywords
            prop_schema = properties.get(prop_name, {})
            # Basic type checking
            if "type" in prop_schema:
                expected = prop_schema["type"]
                actual = type(prop_value).__name__
                type_map = {"str": "string", "int": "integer", "float": "number", "bool": "boolean", "list": "array", "dict": "object"}
                actual_json = type_map.get(actual, actual)
                if expected != actual_json and not (isinstance(expected, list) and actual_json in expected):
                    if expected != "array" or actual_json != "string":  # Allow some flexibility
                        errors.append(f"dataset[{dataset_index}].{field_name}.{prop_name}: Expected type '{expected}', got '{actual_json}'")
        
        if not errors:
            # No specific errors found, give a generic message
            errors.append(f"dataset[{dataset_index}].{field_name}: Object structure doesn't match {expected_type} schema")
    
    elif expected_type and isinstance(field_value, str):
        # It's a string, should be a valid IRI
        if not (field_value.startswith("http://") or field_value.startswith("https://")):
            errors.append(f"dataset[{dataset_index}].{field_name}: String value should be a valid IRI (http:// or https://), got '{field_value[:50]}...'")
        else:
            errors.append(f"dataset[{dataset_index}].{field_name}: IRI reference '{field_value[:60]}...' doesn't resolve or format is invalid")
    
    elif expected_type and isinstance(field_value, list):
        # It's an array (like distribution)
        type_def = defs.get(expected_type, {})
        properties = type_def.get("properties", {})
        
        # Create a mini-schema for validating individual items
        item_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$ref": f"#/$defs/{expected_type}",
            "$defs": defs
        }
        
        for i, item in enumerate(field_value[:5]):  # Check first 5 items
            if isinstance(item, dict):
                try:
                    item_validator = jsonschema_rs.validator_for(item_schema)
                    item_errors = list(item_validator.iter_errors(item))
                    
                    for err in item_errors:
                        err_path = err.instance_path if hasattr(err, 'instance_path') else []
                        err_msg = err.message if hasattr(err, 'message') else str(err)
                        
                        if isinstance(err_path, list) and len(err_path) > 0:
                            sub_field = ".".join(str(p) for p in err_path)
                        else:
                            sub_field = None
                        
                        # Parse the error message for more detail
                        if "is not valid under any of the schemas listed in the 'oneOf'" in err_msg:
                            # Get the field name and check what it expects
                            if sub_field:
                                sub_value = item.get(err_path[0]) if isinstance(err_path, list) else None
                                sub_prop = properties.get(err_path[0], {}) if isinstance(err_path, list) else {}
                                one_of = sub_prop.get("oneOf", [])
                                
                                if one_of and isinstance(sub_value, str):
                                    # String value where object or IRI expected
                                    expected_refs = [o.get("$ref", "").split("/")[-1] for o in one_of if "$ref" in o]
                                    sub_value_display = sub_value[:30] if len(sub_value) > 30 else sub_value
                                    if expected_refs:
                                        errors.append(f"dataset[{dataset_index}].{field_name}[{i}].{sub_field}: Plain string '{sub_value_display}' not allowed. Expected {expected_refs[0]} object or IRI (http://...)")
                                    else:
                                        errors.append(f"dataset[{dataset_index}].{field_name}[{i}].{sub_field}: Plain string '{sub_value_display}' not allowed. Expected object or IRI")
                                else:
                                    errors.append(f"dataset[{dataset_index}].{field_name}[{i}].{sub_field}: Value doesn't match allowed formats")
                            else:
                                errors.append(f"dataset[{dataset_index}].{field_name}[{i}]: Object doesn't match {expected_type} schema")
                        elif "is a required property" in err_msg:
                            prop_name = extract_required_property_name(err_msg)
                            if prop_name:
                                errors.append(f"dataset[{dataset_index}].{field_name}[{i}]: Missing required property '{prop_name}'")
                        else:
                            if sub_field:
                                errors.append(f"dataset[{dataset_index}].{field_name}[{i}].{sub_field}: {err_msg[:100]}")
                            else:
                                errors.append(f"dataset[{dataset_index}].{field_name}[{i}]: {err_msg[:100]}")
                except Exception as e:
                    errors.append(f"dataset[{dataset_index}].{field_name}[{i}]: Validation error - {e}")
    
    if not errors:
        errors.append(f"dataset[{dataset_index}].{field_name}: Value doesn't match expected schema")
    
    return errors


def check_object_against_def(obj, type_def, path_prefix):
    """Check an object against a type definition and return specific errors."""
    errors = []
    properties = type_def.get("properties", {})
    
    for prop_name, prop_value in obj.items():
        if prop_name.startswith("@"):
            continue
        
        if prop_name not in properties:
            # Check if additional properties are allowed
            if type_def.get("additionalProperties") == False:
                errors.append(f"{path_prefix}: Unknown property '{prop_name}'")
    
    return errors


def format_single_error(field_path, message, dataset_index=None):
    """Format a single validation error message into a readable form."""
    prefix = f"dataset[{dataset_index}]" if dataset_index is not None else ""
    
    if field_path and field_path != "(root)":
        location = f"{prefix}.{field_path}" if prefix else field_path
    else:
        location = prefix if prefix else "(root)"
    
    # Parse common error patterns to make them more readable
    if "is a required property" in message:
        prop_name = extract_required_property_name(message)
        if prop_name:
            return f"{location}: Missing required property '{prop_name}'"
        return f"{location}: Missing required property"
    
    elif "is not of type" in message:
        type_match = re.search(r"is not of type '([^']+)'", message)
        if type_match:
            return f"{location}: Expected type '{type_match.group(1)}'"
        return f"{location}: Type mismatch"
    
    elif "is not valid under any of the schemas listed in the 'oneOf'" in message:
        return f"{location}: Value doesn't match any allowed schema pattern (oneOf)"
    
    elif "is not valid under any of the schemas listed in the 'anyOf'" in message:
        return f"{location}: Value doesn't match any allowed schema pattern (anyOf)"
    
    elif "does not match" in message:
        pattern_match = re.search(r"does not match '([^']+)'", message)
        if pattern_match:
            return f"{location}: Format validation failed (pattern: {pattern_match.group(1)[:50]})"
        return f"{location}: Format validation failed"
    
    elif "Additional properties are not allowed" in message:
        props_match = re.search(r"\(([^)]+) (?:was|were) unexpected\)", message)
        if props_match:
            return f"{location}: Additional properties not allowed: {props_match.group(1)}"
        return f"{location}: Contains additional properties not allowed by schema"
    
    else:
        # Truncate very long messages
        if len(message) > 200:
            message = message[:200] + "..."
        return f"{location}: {message}"

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
            print(f"❌ UNEXPECTED: {example_file.name} is invalid but expected to be VALID")
        else:
            print(f"✅ PASS: {example_file.name} is invalid (as expected)")
        
        # Analyze errors and provide detailed feedback
        formatted_errors = []
        dataset_oneOf_errors = []  # Track dataset indices with oneOf errors
        
        # First pass: identify dataset-level oneOf errors vs other errors
        for error in all_errors:
            instance_path = error.instance_path if hasattr(error, 'instance_path') else []
            message = error.message if hasattr(error, 'message') else str(error)
            
            # Check if this is a dataset-level oneOf error
            if (isinstance(instance_path, list) and 
                len(instance_path) == 2 and 
                instance_path[0] == 'dataset' and
                "is not valid under any of the schemas listed in the 'oneOf'" in message):
                # This is a dataset that failed oneOf validation - we need to dig deeper
                dataset_index = instance_path[1]
                dataset_oneOf_errors.append(dataset_index)
            else:
                # Regular error - format it normally
                field_path = get_field_path_from_error(error)
                
                # Handle root-level required property errors nicely
                if field_path == "$" and "is a required property" in message:
                    prop_name = extract_required_property_name(message)
                    if prop_name:
                        formatted_errors.append(f"Catalog: Missing required field '{prop_name}'")
                    else:
                        formatted_errors.append(f"Catalog: Missing required field")
                else:
                    formatted_errors.append(format_single_error(field_path, message))
        
        # Second pass: for dataset oneOf errors, validate each dataset directly
        # against the Dataset schema to get specific field-level errors
        if dataset_oneOf_errors and isinstance(example_data, dict) and 'dataset' in example_data:
            dataset_schema = create_dataset_schema(main_schema)
            datasets = example_data.get('dataset', [])
            
            for dataset_index in dataset_oneOf_errors:
                if dataset_index < len(datasets):
                    dataset_obj = datasets[dataset_index]
                    
                    # Only validate objects, not string IRIs
                    if isinstance(dataset_obj, dict):
                        # Get the dataset title for better identification
                        dataset_title = dataset_obj.get('title', f'(untitled dataset)')
                        if len(dataset_title) > 50:
                            dataset_title = dataset_title[:50] + "..."
                        
                        # Validate directly against Dataset schema
                        dataset_errors = validate_dataset_directly(dataset_obj, dataset_index, dataset_schema)
                        
                        if dataset_errors:
                            # Add a header for this dataset
                            formatted_errors.append(f"dataset[{dataset_index}] \"{dataset_title}\":")
                            for err in dataset_errors:
                                # Indent the sub-errors
                                formatted_errors.append(f"    → {err}")
                        else:
                            formatted_errors.append(f"dataset[{dataset_index}]: Validation failed but no specific errors found")
                    else:
                        formatted_errors.append(f"dataset[{dataset_index}]: Expected object or IRI string, got {type(dataset_obj).__name__}")
        
        # Print results
        total_issues = len(formatted_errors)
        print(f"   Found {len(dataset_oneOf_errors)} dataset(s) with validation issues:")
        print()
        
        for error_msg in formatted_errors:
            print(f"   {error_msg}")
        
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