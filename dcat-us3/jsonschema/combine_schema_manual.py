#!/usr/bin/env python3
"""
Simple Schema Combiner for DCAT-US 3.0

This script combines all the schema definition files into a single
expanded schema with Catalog as the root and all definitions included.
"""

import json
from pathlib import Path
from typing import Dict, Any

def load_json_file(filepath: Path) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to load {filepath}: {e}")
        return {}

def clean_schema_object(obj: Any) -> Any:
    """
    Recursively clean a schema object:
    - Remove "$id" keys
    - Rename "definitions" to "$defs"
    - Update "$ref" paths from "#/definitions/" to "#/$defs/"
    """
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            # Skip $id keys (remove them)
            if key == "$id":
                continue
            
            # Rename "definitions" to "$defs"
            new_key = "$defs" if key == "definitions" else key
            
            # Update $ref paths
            if key == "$ref" and isinstance(value, str):
                cleaned[new_key] = value.replace("#/definitions/", "#/$defs/")
            else:
                # Recursively clean nested objects
                cleaned[new_key] = clean_schema_object(value)
        
        return cleaned
    elif isinstance(obj, list):
        # Recursively clean array items
        return [clean_schema_object(item) for item in obj]
    else:
        # Return primitives as-is
        return obj

def load_all_definitions(definitions_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load all definition files from the definitions directory."""
    definitions = {}
    
    if not definitions_dir.exists():
        print(f"ERROR: Definitions directory not found: {definitions_dir}")
        return definitions
    
    for json_file in definitions_dir.glob("*.json"):
        definition_name = json_file.stem
        definition_data = load_json_file(json_file)
        if definition_data:
            # Clean the definition (remove $id, rename definitions to $defs, update $refs)
            cleaned_data = clean_schema_object(definition_data)
            definitions[definition_name] = cleaned_data
            print(f"Loaded definition: {definition_name}")
    
    return definitions

def create_expanded_schema(definitions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Create the expanded schema with Catalog as root and all definitions included."""
    
    # Get the Catalog definition as the base
    catalog_def = definitions.get("Catalog", {})
    if not catalog_def:
        raise ValueError("Catalog.json not found in definitions directory")
    
    # Use Catalog as the root schema structure
    expanded_schema = catalog_def.copy()
    
    # Add all definitions to the schema
    expanded_schema["$defs"] = definitions
    
    return expanded_schema

def main():
    """Main function to create the expanded DCAT-US 3.0 schema."""
    print("=== DCAT-US 3.0 Simple Schema Combiner ===")
    print()
    
    # Set up paths
    script_dir = Path(__file__).parent
    definitions_dir = script_dir / "definitions"
    output_path = script_dir / "dcat-us3.0-expanded-schema.json"
    
    # Load all definitions
    print(f"Loading definitions from: {definitions_dir}")
    definitions = load_all_definitions(definitions_dir)
    if not definitions:
        print("ERROR: No definitions loaded")
        exit(1)
    
    print(f"Loaded {len(definitions)} definitions")
    print()
    
    # Create expanded schema
    print("Creating expanded schema...")
    try:
        expanded_schema = create_expanded_schema(definitions)
    except ValueError as e:
        print(f"ERROR: {e}")
        exit(1)
    
    # Write the expanded schema
    print(f"Writing expanded schema to: {output_path}")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(expanded_schema, f, indent=2, ensure_ascii=False)
        
        print("✅ Successfully created expanded schema!")
        print(f"📊 Schema size: {len(json.dumps(expanded_schema))} characters")
        print(f"📋 Definitions included: {len(expanded_schema.get('definitions', {}))}")
        
        if expanded_schema.get('type'):
            print(f"📝 Root type: {expanded_schema['type']}")
        if expanded_schema.get('title'):
            print(f"🎯 Title: {expanded_schema['title']}")
            
    except Exception as e:
        print(f"ERROR: Failed to write expanded schema: {e}")
        exit(1)

if __name__ == "__main__":
    main()