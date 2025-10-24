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
import logging

# Suppress pyshacl warnings and rdflib date parsing errors for cleaner output
warnings.filterwarnings("ignore", module="pyshacl")
warnings.filterwarnings("ignore", module="rdflib")
logging.getLogger("rdflib").setLevel(logging.ERROR)

def load_jsonld_file(filepath):
    """Load and parse a JSON-LD file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to load {filepath}: {e}")
        return None

def extract_violation_details(report_graph):
    """Extract structured violation details from SHACL validation report graph."""
    from rdflib import RDF, Namespace
    
    SH = Namespace("http://www.w3.org/ns/shacl#")
    violations = []
    
    # Find all validation results
    for result in report_graph.subjects(RDF.type, SH.ValidationResult):
        violation = {}
        
        # Extract basic violation info
        for severity in report_graph.objects(result, SH.resultSeverity):
            violation['severity'] = str(severity).split('#')[-1] if '#' in str(severity) else str(severity)
        
        for source_shape in report_graph.objects(result, SH.sourceShape):
            shape_str = str(source_shape)
            # Extract shape name from URI
            if '#' in shape_str:
                violation['source_shape'] = shape_str.split('#')[-1]
            elif '/' in shape_str:
                violation['source_shape'] = shape_str.split('/')[-1]
            else:
                violation['source_shape'] = shape_str
        
        for focus_node in report_graph.objects(result, SH.focusNode):
            violation['focus_node'] = str(focus_node)
        
        for result_path in report_graph.objects(result, SH.resultPath):
            path_str = str(result_path)
            # Extract property name from URI
            if '#' in path_str:
                violation['result_path'] = path_str.split('#')[-1]
            elif '/' in path_str:
                violation['result_path'] = path_str.split('/')[-1]
            else:
                violation['result_path'] = path_str
        
        for message in report_graph.objects(result, SH.resultMessage):
            violation['message'] = str(message)
        
        for value in report_graph.objects(result, SH.value):
            # Try to extract a more readable representation of the value
            value_str = str(value)
            if value_str.startswith('_:'):  # Blank node
                # Try to find a better description of the blank node
                value_description = describe_blank_node(report_graph, value)
                violation['value'] = value_description or '[blank node]'
                violation['value_node'] = value  # Keep the actual node for further analysis
            else:
                violation['value'] = value_str
                # Even non-blank nodes could be dataset objects in the data graph
                violation['value_node'] = value
        
        # Extract constraint component info
        for constraint in report_graph.objects(result, SH.sourceConstraintComponent):
            constraint_str = str(constraint)
            if '#' in constraint_str:
                violation['constraint_component'] = constraint_str.split('#')[-1]
            else:
                violation['constraint_component'] = constraint_str
        
        violations.append(violation)
    
    return violations

def analyze_blank_node_violations(data_graph, value_node):
    """Analyze what's wrong with a blank node (dataset object)."""
    from rdflib import RDF, Namespace, Literal
    
    # Use the correct namespace prefixes based on the JSON-LD context
    DCAT = Namespace("http://www.w3.org/ns/dcat#")
    DC = Namespace("http://purl.org/dc/terms/")
    POD = Namespace("https://project-open-data.cio.gov/v1.1/schema#")
    DCTERMS = Namespace("http://purl.org/dc/terms/")  # Alternative namespace
    
    analysis = []
    
    # Check if it has a type
    types = list(data_graph.objects(value_node, RDF.type))
    if not types:
        analysis.append("❌ Missing @type field (should be 'dcat:Dataset')")
    elif not any('Dataset' in str(t) for t in types):
        type_names = [str(t).split('#')[-1] if '#' in str(t) else str(t).split('/')[-1] for t in types]
        analysis.append(f"❌ Wrong type: {', '.join(type_names)} (should be 'dcat:Dataset')")
    
    # Check for @id (which would make it an IRI instead of blank node)
    analysis.append("❌ Missing @id field (datasets should have unique identifiers like 'http://example.com/dataset/1')")
    
    # Get all properties to understand what's actually in this dataset
    all_props = {}
    for pred, obj in data_graph.predicate_objects(value_node):
        prop_name = str(pred).split('#')[-1] if '#' in str(pred) else str(pred).split('/')[-1]
        if isinstance(obj, Literal):
            all_props[prop_name] = str(obj)[:50] + ("..." if len(str(obj)) > 50 else "")
        else:
            all_props[prop_name] = f"[{type(obj).__name__}]"
    
    # Check for required fields based on actual property names in the data
    found_props = set(all_props.keys())
    
    # Map common property variations
    property_mappings = {
        'title': ['title'],
        'description': ['description'], 
        'identifier': ['identifier'],
        'modified': ['modified'],
        'accessLevel': ['accessLevel'],
        'bureauCode': ['bureauCode'],
        'programCode': ['programCode'],
        'contactPoint': ['contactPoint'],
        'distribution': ['distribution'],
        'keyword': ['keyword']
    }
    
    missing_required = []
    malformed_fields = []
    
    # Check what's missing vs what's present
    for standard_name, variations in property_mappings.items():
        found = any(var in found_props for var in variations)
        if standard_name in ['title', 'description', 'identifier', 'modified', 'accessLevel', 'bureauCode', 'programCode']:
            if not found:
                missing_required.append(standard_name)
    
    # Check for malformed fields that are present
    if 'modified' in found_props:
        mod_val = all_props['modified']
        if 'R/P' in mod_val and not ('2' in mod_val and '-' in mod_val):
            malformed_fields.append(f"modified: '{mod_val}' (should be ISO date like '2023-01-01' or full ISO duration)")
    
    if missing_required:
        analysis.append(f"❌ Missing required fields: {', '.join(missing_required)}")
    
    if malformed_fields:
        analysis.append(f"⚠️  Malformed fields: {', '.join(malformed_fields)}")
    
    # Show what fields ARE present for context
    if all_props:
        present_fields = list(all_props.keys())[:8]  # Show first 8 fields
        more_text = f" (+{len(all_props) - 8} more)" if len(all_props) > 8 else ""
        analysis.append(f"📋 Found fields: {', '.join(present_fields)}{more_text}")
    
    return analysis

def find_dataset_nodes_in_data(data_graph):
    """Find all dataset nodes in the data graph."""
    from rdflib import RDF, Namespace
    DCAT = Namespace("http://www.w3.org/ns/dcat#")
    
    catalogs = list(data_graph.subjects(RDF.type, DCAT.Catalog))
    dataset_nodes = []
    
    for catalog in catalogs:
        datasets = list(data_graph.objects(catalog, DCAT.dataset))
        dataset_nodes.extend(datasets)
    
    return dataset_nodes

def format_violation_summary(violations, data_graph):
    """Format violations in a human-readable way."""
    if not violations:
        return "No specific violation details could be extracted."
    
    summary = []
    other_violations = []
    dataset_violation_count = 0
    
    # Check if we have dataset violations by looking at the pattern
    for i, violation in enumerate(violations, 1):
        if (violation.get('constraint_component') == 'OrConstraintComponent' and 
            violation.get('result_path') == 'dataset'):
            dataset_violation_count += 1
        else:
            other_violations.append((i, violation))
    
    # Show other violations first if any
    for i, violation in other_violations:
        lines = [f"\n❌ VIOLATION #{i}:"]
        
        if 'source_shape' in violation:
            lines.append(f"   Shape: {violation['source_shape']}")
        
        if 'constraint_component' in violation:
            constraint = violation['constraint_component']
            if constraint == 'OrConstraintComponent':
                lines.append(f"   Issue: Must match one of several allowed patterns/types")
            elif constraint == 'ClassConstraintComponent':
                lines.append(f"   Issue: Value must be of the correct class/type")
            elif constraint == 'DatatypeConstraintComponent':
                lines.append(f"   Issue: Value must be of the correct datatype")
            elif constraint == 'NodeKindConstraintComponent':
                lines.append(f"   Issue: Value must be the right kind of node (IRI, literal, etc.)")
            elif constraint == 'MinCountConstraintComponent':
                lines.append(f"   Issue: Missing required field (minimum count not met)")
            elif constraint == 'MaxCountConstraintComponent':
                lines.append(f"   Issue: Too many values for this field")
            else:
                lines.append(f"   Constraint: {constraint}")
        
        if 'result_path' in violation:
            lines.append(f"   Property: {violation['result_path']}")
        
        if 'focus_node' in violation:
            node = violation['focus_node']
            if len(node) > 80:
                node = node[:80] + "..."
            lines.append(f"   Focus Node: {node}")
        
        if 'value' in violation and violation['value'] != violation.get('focus_node'):
            value = violation['value']
            if len(value) > 100:
                value = value[:100] + "..."
            lines.append(f"   Problematic Value: {value}")
        
        if 'message' in violation:
            msg = violation['message']
            if len(msg) > 200:
                msg = msg[:200] + "..."
            lines.append(f"   Message: {msg}")
        
        summary.extend(lines)
    
    # Handle dataset violations
    if dataset_violation_count > 0:
        if other_violations:
            summary.append("\n" + "="*60)
        
        summary.append(f"\n🔍 DETAILED DATASET ANALYSIS:")
        summary.append(f"Found {dataset_violation_count} datasets with validation issues:")
        summary.append(f"💡 ROOT CAUSE: Datasets are embedded as objects but should be referenced by IRI\n")
        
        # Analyze the actual dataset nodes in the data
        dataset_nodes = find_dataset_nodes_in_data(data_graph)
        
        for i, dataset_node in enumerate(dataset_nodes[:dataset_violation_count], 1):
            analysis = analyze_blank_node_violations(data_graph, dataset_node)
            summary.append(f"📦 Dataset #{i}:")
            for issue in analysis:
                summary.append(f"   {issue}")
            summary.append("")  # Empty line between datasets
        
        summary.append("🔧 SOLUTION: Add '@id' field to each dataset object, for example:")
        summary.append('   "dataset": [')
        summary.append('     {')
        summary.append('       "@id": "http://www.cftc.gov/data.json#dataset-1",')
        summary.append('       "@type": "dcat:Dataset",')
        summary.append('       "title": "Your Dataset Title",')
        summary.append('       ...')
        summary.append('     }')
        summary.append('   ]')
    
    return '\n'.join(summary)

def describe_blank_node(graph, blank_node):
    """Try to describe a blank node in a more readable way."""
    from rdflib import RDF, RDFS
    
    # Look for type information
    types = list(graph.objects(blank_node, RDF.type))
    if types:
        type_str = str(types[0])
        if '#' in type_str:
            type_name = type_str.split('#')[-1]
        elif '/' in type_str:
            type_name = type_str.split('/')[-1]
        else:
            type_name = type_str
        return f"[{type_name} object]"
    
    # Look for title, name, or identifier
    from rdflib import Literal, Namespace
    DC = Namespace("http://purl.org/dc/terms/")
    DCAT = Namespace("http://www.w3.org/ns/dcat#")
    
    for prop in [DC.title, DC.identifier, RDFS.label]:
        values = list(graph.objects(blank_node, prop))
        if values:
            return f"[object with {prop.split('#')[-1] if '#' in str(prop) else str(prop)}: {values[0]}]"
    
    return None

def analyze_data_issues(example_file, data_graph):
    """Analyze the actual data to provide more context about issues."""
    analysis = []
    
    # Check for datasets without @id
    from rdflib import RDF, Namespace
    DCAT = Namespace("http://www.w3.org/ns/dcat#")
    
    catalogs = list(data_graph.subjects(RDF.type, DCAT.Catalog))
    if catalogs:
        catalog = catalogs[0]
        datasets = list(data_graph.objects(catalog, DCAT.dataset))
        
        blank_datasets = [d for d in datasets if str(d).startswith('_:')]
        if blank_datasets:
            analysis.append(f"📌 ANALYSIS: Found {len(blank_datasets)} datasets without IDs")
            analysis.append("   💡 SUGGESTION: Add '@id' field to each dataset object")
            analysis.append("   Example: {\"@id\": \"http://example.com/dataset/1\", \"@type\": \"dcat:Dataset\", ...}")
    
    return analysis

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
            print(f"✅ SUCCESS: {example_file.name} conforms to DCAT-US 3.0 SHACL shapes")
            return True
        else:
            print(f"❌ FAILURE: {example_file.name} does not conform to DCAT-US 3.0 SHACL shapes")
            
            # Extract structured violation details
            violations = extract_violation_details(report_graph)
            
            if violations:
                print(f"\n📋 VALIDATION ISSUES FOUND ({len(violations)} total):")
                print(format_violation_summary(violations, data_graph))
                
                # Add data analysis
                analysis = analyze_data_issues(example_file, data_graph)
                if analysis:
                    print(f"\n🔍 DATA ANALYSIS:")
                    for line in analysis:
                        print(line)
            else:
                print("\n⚠️  Raw validation report (parsing failed):")
                print(report_text)
            
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
    good_dir = examples_dir / "good"
    bad_dir = examples_dir / "bad"
    
    # Check directories exist
    if not examples_dir.exists():
        print(f"ERROR: Examples directory not found: {examples_dir}")
        sys.exit(3)
    
    if not good_dir.exists():
        print(f"ERROR: Good examples directory not found: {good_dir}")
        sys.exit(3)
        
    if not bad_dir.exists():
        print(f"ERROR: Bad examples directory not found: {bad_dir}")
        sys.exit(3)
    
    # Find JSON-LD files in good and bad directories
    good_files = list(good_dir.glob("*.jsonld")) + list(good_dir.glob("*.json"))
    bad_files = list(bad_dir.glob("*.jsonld")) + list(bad_dir.glob("*.json"))
    
    if not good_files and not bad_files:
        print(f"WARNING: No JSON-LD files found in {good_dir} or {bad_dir}")
        sys.exit(0)
    
    print(f"Found {len(good_files)} files in 'good' directory")
    print(f"Found {len(bad_files)} files in 'bad' directory")
    print("=" * 60)
    
    # Track validation results and expectations
    good_passed = 0
    good_failed = 0
    bad_passed = 0
    bad_failed = 0
    good_failed_files = []
    bad_passed_files = []
    
    # Validate good examples (should pass)
    if good_files:
        print("=== VALIDATING 'GOOD' EXAMPLES (Expected to PASS) ===")
        for example_file in sorted(good_files):
            print(f"Validating: {example_file}")
            if validate_example(example_file, shapes_graph):
                good_passed += 1
            else:
                good_failed += 1
                good_failed_files.append(str(example_file))
            print()
    
    # Validate bad examples (should fail)
    if bad_files:
        print("=== VALIDATING 'BAD' EXAMPLES (Expected to FAIL) ===")
        for example_file in sorted(bad_files):
            print(f"Validating: {example_file}")
            if validate_example(example_file, shapes_graph):
                bad_passed += 1
                bad_passed_files.append(str(example_file))
            else:
                bad_failed += 1
            print()
    
    # Summary with expectation analysis
    print("=" * 60)
    print("📊 SHACL VALIDATION SUMMARY:")
    print(f"  Good examples processed: {len(good_files)}")
    print(f"    ✅ Passed (expected): {good_passed}")
    print(f"    ❌ Failed (unexpected): {good_failed}")
    print(f"  Bad examples processed: {len(bad_files)}")
    print(f"    ❌ Failed (expected): {bad_failed}")
    print(f"    ✅ Passed (unexpected): {bad_passed}")
    print()
    
    # Report unexpected results
    unexpected_results = False
    
    if good_failed_files:
        unexpected_results = True
        print("🚨 UNEXPECTED FAILURES (files in 'good' that failed validation):")
        for filepath in good_failed_files:
            print(f"  - {filepath}")
        print()
    
    if bad_passed_files:
        unexpected_results = True
        print("🚨 UNEXPECTED PASSES (files in 'bad' that passed validation):")
        for filepath in bad_passed_files:
            print(f"  - {filepath}")
        print()
    
    if not unexpected_results:
        print("🎉 ALL RESULTS MATCH EXPECTATIONS!")
        print("  - All 'good' examples passed validation")
        print("  - All 'bad' examples failed validation")
    
    # Exit with appropriate code
    if unexpected_results:
        sys.exit(1)
    else:
        print("✅ Validation completed successfully with expected results")

if __name__ == "__main__":
    main()