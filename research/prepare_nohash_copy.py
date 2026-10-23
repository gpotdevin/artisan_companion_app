#!/usr/bin/env python3
"""Prepare a no-hash/signature copy for M0 manual check.

Loads an .alog file, deletes the top-level "hash" and "signature" keys if present,
and writes it back using Python's repr() which matches Artisan's serialization format.

Usage:
    python prepare_nohash_copy.py <input.alog> <output.alog>
"""

import ast
import sys
from pathlib import Path


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


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.alog> <output.alog>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    data = load_alog(input_path)
    
    # Delete hash and signature if present
    hash_present = 'hash' in data
    signature_present = 'signature' in data
    
    if hash_present:
        del data['hash']
    if signature_present:
        del data['signature']
    
    write_alog(output_path, data)
    
    # Verify the output parses
    verify_data = load_alog(output_path)
    
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"\nRemoved keys:")
    print(f"  hash: {'YES' if hash_present else 'NO (not present)'}")
    print(f"  signature: {'YES' if signature_present else 'NO (not present)'}")
    print(f"\nVerification: output parses {'OK' if isinstance(verify_data, dict) else 'FAILED'}")
    print(f"  hash in output: {'YES' if 'hash' in verify_data else 'NO'}")
    print(f"  signature in output: {'YES' if 'signature' in verify_data else 'NO'}")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
