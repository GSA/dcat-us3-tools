#!/usr/bin/env python3
"""
Fix distribution mediaType and format fields for DCAT-US 3.0 compliance.

Transforms string values like:
    "mediaType": "application/json"
To object format:
    "mediaType": {"label": "application/json"}

Usage:
    python fix_distribution_formats.py <input_file> [output_file]
    
If output_file is not specified, overwrites the input file.
"""

import json
import sys


def fix_distribution(dist):
    """Fix mediaType and format fields in a distribution object."""
    for field in ['mediaType', 'format']:
        if field in dist and isinstance(dist[field], str):
            dist[field] = {"label": dist[field]}
    return dist


def fix_dataset(dataset):
    """Fix all distributions in a dataset, and fix spatial field."""
    if 'distribution' in dataset and isinstance(dataset['distribution'], list):
        dataset['distribution'] = [fix_distribution(d) for d in dataset['distribution']]
    if 'spatial' in dataset and isinstance(dataset['spatial'], str):
        dataset['spatial'] = {"prefLabel": dataset['spatial']}
    return dataset


def fix_catalog(data):
    """Fix all datasets in a catalog."""
    if 'dataset' in data and isinstance(data['dataset'], list):
        data['dataset'] = [fix_dataset(ds) for ds in data['dataset']]
    return data


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fix_catalog(data)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Fixed: {input_file} -> {output_file}")


if __name__ == "__main__":
    main()
