#!/usr/bin/env python3
"""
Verify Artisan 4.2 profile hash against the reverse-engineered algorithm.

Usage:
    py -3 verify_profile_hash.py <manifest>

Where <manifest> is a text file with one .alog path per line.

For each file, prints MATCH or MISMATCH with stored vs computed hash.
Exits 0 iff all files match.
"""

import ast
import hashlib
import json
import sys


def rec_int_to_float(data):
    """
    Recursively convert every int (including bool) to float.
    
    Matches Artisan's artisanlib/util.py:rec_int_to_float exactly:
    - int -> float (including True -> 1.0, False -> 0.0)
    - dict -> dict with values converted
    - list -> list with elements converted
    - other types unchanged
    """
    if isinstance(data, int):
        # bool is a subclass of int in Python, so this catches True/False too
        return float(data)
    if isinstance(data, dict):
        return {k: rec_int_to_float(v) for k, v in data.items()}
    if isinstance(data, list):
        return [rec_int_to_float(v) for v in data]
    return data


def compute_profile_hash(profile):
    """
    Compute the Artisan 4.2 profile hash.
    
    Algorithm (reverse-engineered from artisanlib/main.py validateProfileDict):
    1. Remove 'hash' key from profile copy
    2. Apply rec_int_to_float to the entire dict
    3. Serialize with json.dumps(sort_keys=True, ensure_ascii=True, separators=(',',':'))
    4. SHA256 hexdigest of the UTF-8 bytes
    """
    p = dict(profile)
    p.pop("hash", None)
    blob = json.dumps(
        rec_int_to_float(p),
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":")
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_alog(path):
    """Load an .alog file using ast.literal_eval."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return ast.literal_eval(content)


def main():
    if len(sys.argv) != 2:
        print("Usage: py -3 verify_profile_hash.py <manifest>", file=sys.stderr)
        sys.exit(1)

    manifest_path = sys.argv[1]
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        paths = [line.strip() for line in f if line.strip()]
    
    if not paths:
        print("Manifest is empty.", file=sys.stderr)
        sys.exit(1)

    all_match = True
    for path in paths:
        try:
            profile = load_alog(path)
            stored_hash = profile.get("hash")
            
            if stored_hash is None:
                print(f"SKIP (no hash) {path}")
                continue
            
            computed_hash = compute_profile_hash(profile)
            
            if stored_hash == computed_hash:
                print(f"MATCH {path}")
            else:
                print(f"MISMATCH {path} (stored={stored_hash}, computed={computed_hash})")
                all_match = False
        except Exception as e:
            print(f"ERROR {path}: {e}", file=sys.stderr)
            all_match = False
    
    if all_match:
        print(f"\nAll {len(paths)} files matched.")
        sys.exit(0)
    else:
        print("\nSome files did not match.")
        sys.exit(1)


if __name__ == "__main__":
    main()
