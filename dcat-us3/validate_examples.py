#!/usr/bin/env python3
"""
DCAT-US 3.0 SHACL Validator

This script validates JSON-LD examples against the DCAT-US 3.0 SHACL shapes.

Usage:
    python validate_shacl.py                    # Validate all files in examples/ directory
    python validate_shacl.py <jsonld_file>      # Validate a specific JSON-LD file
"""

import json
import sys
from pathlib import Path
from pyshacl import validate
from rdflib import Graph
import warnings

# Suppress pyshacl warnings for cleaner output
warnings.filterwarnings("ignore", module="pyshacl")

def load_jsonld_file(filepath):
    """Load and parse a JSON-LD file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to load {filepath}: {e}")
        return None

def validate_example(example_file, shapes_graph):
    """Validate a single JSON-LD example file against the SHACL shapes."""
    example_data = load_jsonld_file(example_file)
    if example_data is None:
        return False
    
    try:
        # Parse the JSON-LD data into an RDF graph
        data_graph = Graph()
        data_graph.parse(data=example_data, format='json-ld')
        print(f"  Loaded {len(data_graph)} triples from {example_file.name}")
        
        # Perform SHACL validation
        conforms, report_graph, report_text = validate(
            data_graph=data_graph,
            shacl_graph=shapes_graph,
            inference='rdfs',
            abort_on_first=False,
            allow_infos=False,
            allow_warnings=False,
            debug=False,
            advanced=True
        )
        
        if conforms:
            print(f"SUCCESS: {example_file.name} conforms to DCAT-US 3.0 SHACL shapes")
            return True
        else:
            print(f"FAILURE: {example_file.name} does not conform to DCAT-US 3.0 SHACL shapes")
            print("\nDetailed Validation Report:")
            print(report_text)
            
            # Extract and display specific violations in a more structured way
            violations = []
            current_violation = []
            
            for line in report_text.split('\n'):
                line = line.strip()
                if not line:
                    if current_violation:
                        violations.append(' '.join(current_violation))
                        current_violation = []
                    continue
                    
                if any(keyword in line for keyword in ['Constraint Violation', 'Severity', 'Source Shape', 'Focus Node', 'Result Path', 'Value']):
                    current_violation.append(line)
            
            # Add any remaining violation
            if current_violation:
                violations.append(' '.join(current_violation))
            
            if violations:
                print(f"\nSpecific Violations Summary ({len(violations)} total):")
                for i, violation in enumerate(violations[:10], 1):
                    print(f"  {i}. {violation}")
                if len(violations) > 10:
                    print(f"  ... and {len(violations) - 10} more violations")
            
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

    print("=== DCAT-US 3.0 SHACL Validation ===")
    print()

    # Load SHACL shapes
    print("Loading SHACL shapes...")
    shapes_file = Path(__file__).parent / "dcat-us_3.0_shacl_shapes.ttl"

    if not shapes_file.exists():
        print(f"ERROR: SHACL shapes file {shapes_file} not found")
        sys.exit(1)
    
    try:
        shapes_graph = Graph()
        shapes_graph.parse(str(shapes_file), format='turtle')
        print(f"Loaded {len(shapes_graph)} triples from SHACL shapes")
    except Exception as e:
        print(f"ERROR: Failed to load SHACL shapes: {e}")
        sys.exit(2)
    
    # Check for command-line arguments for single file validation
    if len(sys.argv) == 2:
        # Single file validation mode (like debug_validate.py)
        jsonld_file = Path(sys.argv[1])

        if not jsonld_file.exists():
            print(f"ERROR: File {jsonld_file} not found")
            sys.exit(1)
        
        print(f"\n=== VALIDATION RESULTS FOR {jsonld_file} ===")
        success = validate_example(jsonld_file, shapes_graph)
        sys.exit(0 if success else 1)
    elif len(sys.argv) > 2:
        print("ERROR: Too many arguments provided")
        print(__doc__)
        sys.exit(1)
    
    # Set up paths for directory validation mode
    script_dir = Path(__file__).parent
    examples_dir = script_dir / "examples"
    
    # Find all JSON-LD example files
    if not examples_dir.exists():
        print(f"ERROR: Examples directory not found: {examples_dir}")
        sys.exit(3)
    
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
        if validate_example(example_file, shapes_graph):
            success_count += 1
        else:
            failure_count += 1
        print()  # Add spacing between results
    
    # Summary
    print("=" * 60)
    print("SHACL VALIDATION SUMMARY:")
    print(f"  Total files processed: {len(jsonld_files)}")
    print(f"  Successful validations: {success_count}")
    print(f"  Failed validations: {failure_count}")
    
    if failure_count > 0:
        sys.exit(1)
    else:
        print("All validations passed successfully")

if __name__ == "__main__":
    main()