#!/usr/bin/env python3
"""Rewrite script for M0 round-trip experiment.

Loads an .alog file, updates native sensory fields (flavors, flavorlabels,
cuppingnotes, defect booleans), and writes it back using Python's repr()
which matches Artisan's serialization format exactly.

Usage:
    python rewrite_native_fields.py <input.alog> <output.alog>
"""

import ast
import sys
from pathlib import Path

FLAVOR_FIELDS = ['flavors', 'flavorlabels', 'cuppingnotes']
DEFECT_FIELDS = ['heavyFC', 'lowFC', 'lightCut', 'darkCut', 'drops',
                 'oily', 'uneven', 'tipping', 'scorching', 'divots']


def load_alog(path):
    p = Path(path)
    raw = p.read_bytes()
    if raw[:1] != b'{':
        raise ValueError(f"{p}: not an Artisan pydump")
    try:
        data = ast.literal_eval(raw.decode('utf-8'))
    except (SyntaxError, ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError(f"{p}: pydump parse failed ({exc})") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{p}: top-level object is not a dict")
    return data


def write_alog(path, data):
    p = Path(path)
    serialized = repr(data)
    p.write_text(serialized, encoding='utf-8')


def update_native_fields(data):
    old_values = {}
    new_values = {}
    
    old_values['flavors'] = data.get('flavors', [5.0] * 9)
    data['flavors'] = [8.5, 7.5, 9.0, 8.0, 8.5, 8.0, 9.0, 8.5, 8.0]
    new_values['flavors'] = data['flavors']
    
    old_values['flavorlabels'] = data.get('flavorlabels', 
        ['Acidity', 'Aftertaste', 'Clean Cup', 'Head', 'Fragrance',
         'Sweetness', 'Aroma', 'Balance', 'Body'])
    data['flavorlabels'] = ['Fruit Acidity', 'Floral', 'Clean Cup', 'Body', 'Complexity',
                           'Sweetness', 'Aroma', 'Balance', 'Aftertaste']
    new_values['flavorlabels'] = data['flavorlabels']
    
    old_values['cuppingnotes'] = data.get('cuppingnotes', '')
    data['cuppingnotes'] = 'Bright citrus, floral jasmine, honey sweetness, clean finish'
    new_values['cuppingnotes'] = data['cuppingnotes']
    
    for field in DEFECT_FIELDS:
        old_values[field] = data.get(field, False)
        data[field] = (field in ['tipping', 'scorching'])
        new_values[field] = data[field]
    
    return old_values, new_values


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.alog> <output.alog>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    data = load_alog(input_path)
    old_values, new_values = update_native_fields(data)
    write_alog(output_path, data)
    verify_data = load_alog(output_path)
    
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"\nFields changed:")
    for key in FLAVOR_FIELDS + DEFECT_FIELDS:
        old = old_values.get(key)
        new = verify_data.get(key)
        status = "CHANGED" if old != new else "UNCHANGED"
        print(f"  {key}: {status} (was={old}, now={new})")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
